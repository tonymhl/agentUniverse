#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) Antfin, Inc. All rights reserved.
# @Time    : 2024/12/6 17:54
# @Author  : tonymhl
# @email   : mahongli.mhl@antgroup.com
# @Version : Python3
# @File    : frontend_utils.py
# @Software: PyCharm

import warnings

warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
from typing import Dict, Optional
# from agentuniverse.base.util.logging.logging_util import LOGGER
from sample_standard_app.platform.findata_framework.operator.sdk.dfdatap_sdk_operator import DfDatapSDKOperatorQE
from sample_standard_app.platform.base_lib.logger.logger_conf import Logger
from sample_standard_app.platform.base_lib.logger.logger_type import LoggerType
from agentuniverse_ant_ext.connector.oceanbase.universal_ob_operator import UniversalOBOperator
from agentuniverse_ant_ext.connector.odps.universal_odps_operator import UniversalODPSOperator
import re
from pandas.core.generic import NDFrame
from dfdatapsdk import dfd_client
from dfdatapsdk.configs.sys_config import SysConfig

# 配置 SysConfig
SysConfig.set_app_name("finassetpreference")
SysConfig.set_db_mode("dev")
SysConfig.set_token("fap.antalpha.2A")


class IndicatorDataStore:
    """
    Utility class to store and retrieve indicator data.
    """

    def __init__(self):
        self._store: Dict[str, pd.DataFrame] = {}

    def add_indicator(self, indicator_code: str, data: pd.DataFrame):
        """
        Add indicator data to the store.
        """
        self._store[indicator_code] = data
        print(f"Indicator {indicator_code} added to store.")

    def get_indicator_data(self, indicator_code: str) -> Optional[pd.DataFrame]:
        """
        Retrieve indicator data from the store.
        """
        return self._store.get(indicator_code, None)

    def is_filled(self) -> bool:
        """
        Check if all required indicators are filled.
        """
        return len(self._store) > 0

    def clear(self):
        """
        Clear the store.
        """
        self._store.clear()


# 序列化函数
def default_handler(obj):
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()  # 将 Timestamp 转换为 ISO 格式的字符串
    elif isinstance(obj, NDFrame):  # 如果对象是 DataFrame 或 Series，则转换为字典
        return obj.to_dict(orient='records') if hasattr(obj, 'to_dict') else None
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def convert_indicator_data_to_df(indicator_data):
    """
    Convert indicator data from list of dicts to pandas DataFrame.

    Args:
        indicator_data (list): List of indicator data dictionaries

    Returns:
        dict: Dictionary mapping indicator codes to pandas DataFrames
    """
    result = {}
    for indicator in indicator_data:
        code = indicator['指标代码']
        df = pd.DataFrame(indicator['数据'])
        result[code] = df
    return result


def filter_with_asset_pool(indicator_data, sec_filter):
    """
    根据产品池筛选产品数据。

    Args:
        indicator_data (dict): 指标数据，字典格式，键为指标代码，值为pandas DataFrame。
        sec_filter (dict): 筛选条件，包括产品池信息和时间范围。

    Returns:
        dict: 筛选后的指标数据，格式与输入相同。
    """
    # 获取筛选条件中的产品池名称
    product_pool = sec_filter.get('产品池')
    start_date = pd.to_datetime(sec_filter.get('开始时间'))
    end_date = pd.to_datetime(sec_filter.get('截止时间'))

    # 查询产品池信息
    odps_sql = f'''
        SELECT  secucode       AS fund_code
                ,classifyresut AS classify_resut
                ,CASE
                   WHEN classifyresut IN ( '固收_中长期纯债' , '固收_低波' ) THEN 'BOND#STABLE#FIXED_INCOME'
                   WHEN classifyresut IN ( '中波固收+' , '高波固收+' )    THEN 'BOND#FIXED_INCOME_POSITIVE'
                   WHEN classifyresut IN ( '短债', '中短债' )                 THEN 'BOND#STEADY'
                   ELSE NULL
                 END           AS classify_resut_code
                ,tradingdate   AS the_datetime
        FROM    antefi.adm_efi_fund_classification_r_bond_full_v2_compare
        where dt=MAX_PT('antefi.adm_efi_fund_classification_r_bond_full_v2_compare')
        and ifmaincode =1
    '''
    df_bondfund = UniversalODPSOperator.execute_sql(odps_sql)

    # 筛选出与指定产品池匹配的基金代码
    target_code = None
    if product_pool == '固收+':
        target_code = 'BOND#FIXED_INCOME_POSITIVE'
    elif product_pool == '固收':
        target_code = 'BOND#STABLE#FIXED_INCOME'
    elif product_pool == '纯债':
        target_code = 'BOND#STEADY'

    if not target_code:
        print("Invalid product pool specified.")
        return indicator_data

    # 筛选符合产品池的基金代码
    filtered_fund_codes = df_bondfund[
        (df_bondfund['classify_resut_code'] == target_code) &
        (pd.to_datetime(df_bondfund['the_datetime']) >= start_date) &
        (pd.to_datetime(df_bondfund['the_datetime']) <= end_date)
        ]['fund_code'].unique()

    # 根据筛选出的基金代码过滤指标数据
    filtered_indicator_data = {}
    for code, df in indicator_data.items():
        # 只保留属于筛选基金代码范围内的数据
        filtered_df = df[df['symbol'].isin(filtered_fund_codes)]
        filtered_indicator_data[code] = filtered_df

    return filtered_indicator_data


def extract_code_from_output(output_text: str) -> str:
    """
    Extract Python code from the output text that's wrapped in ```python ... ``` markers.

    Args:
        output_text (str): The output text containing the code block

    Returns:
        str: The extracted Python code, or empty string if no code found
    """
    import re

    # Pattern to match code between ```python and ``` markers
    pattern = r'```python\n(.*?)```'
    match = re.search(pattern, output_text, re.DOTALL)

    if match:
        return match.group(1).strip()
    return ""


def extract_debug_result(output: str) -> str:
    """
    Extract debugging information from the output text that's wrapped in ```debug ... ``` markers.

    Args:
        output_text (str): The output text containing the debug info

    Returns:
        str: The extracted debug info, or empty string if no debug info found
    """
    # 找到 ```python 的位置
    start_index = output.rfind('```python')
    if start_index != -1:
        # 找到紧接着的下一个 ``` 的位置
        end_index = output.find('```', start_index + len('```python'))
        if end_index != -1:
            # 提取 ```python ... ``` 块的内容
            block_content = output[start_index + len('```python'):end_index].strip()
            # 获取最后一行
            last_line = block_content.split('\n')[-1].strip()
            # 检查是否是 True
            debug_result = (last_line == 'True')
        else:
            debug_result = False  # 没有找到结束标记
    else:
        debug_result = False  # 没有找到开始标记

    return debug_result


def extract_boolean(debug_result):
    # 检查 debug_result 是否是布尔值
    if isinstance(debug_result, bool):
        return debug_result

    # 检查 debug_result 是否是字符串，并包含 'True' 或 'False'
    elif isinstance(debug_result, str):
        # 去除字符串两端的空白字符，并转换为小写进行比较（为了处理可能的大小写不一致）
        cleaned_result = debug_result.strip().lower()
        if cleaned_result == 'True':
            return True
        elif cleaned_result == 'False':
            return False
        else:
            # 如果字符串不包含 'True' 或 'False'，则抛出一个异常或返回 None（根据你的需求）
            # 这里我们返回 None 表示无法从字符串中提取布尔值
            return None

    # 如果 debug_result 不是布尔值或字符串，则抛出一个异常或返回 None（根据你的需求）
    # 这里我们返回 None 表示无法从未知类型中提取布尔值
    return None


def execute_filter_code(code_str: str, indicator_data: dict) -> pd.DataFrame:
    """
    Execute the generated filter code with the provided indicator data.

    Args:
        code_str (str): The Python code to execute
        indicator_data (dict): Dictionary mapping indicator codes to DataFrames

    Returns:
        pd.DataFrame: The filtered results
    """
    try:
        # Create a new sandbox for execution
        sandbox = {
            'pd': pd,
            'np': np,
            'indicator_data': indicator_data
        }

        # Execute the code in the sandbox
        exec(code_str, sandbox)

        # The filter_products function should be defined now
        if 'filter_products' not in sandbox:
            raise ValueError("Code did not define filter_products function")

        # Call the filter function with the indicator data dictionary
        result = sandbox['filter_products'](indicator_data)
        return result

    except Exception as e:
        Logger(__name__, LoggerType.SLS).error(f"Error executing filter code: {str(e)}")
        raise


def execute_calculation_code(code_str: str, NV_data: pd.DataFrame) -> pd.DataFrame:
    """
    Execute the generated calculation code with the provided indicator data.

    Args:
        code_str (str): The Python code to execute
        indicator_data (dict): Dictionary mapping indicator codes to DataFrames

    Returns:
        pd.DataFrame: The calculated results
    """
    try:
        # Create a new sandbox for execution
        sandbox = {
            'pd': pd,
            'np': np,
            'NV_data': NV_data
        }

        # Execute the code in the sandbox
        exec(code_str, sandbox)

        # The calculate_indicator function should be defined now
        if 'calculate_indicator' not in sandbox:
            raise ValueError("Code did not define calculate_indicator function")

        # Call the calculation function with the indicator data
        result = sandbox['calculate_indicator'](NV_data)
        return result

    except Exception as e:
        Logger(__name__, LoggerType.SLS).error(f"Error executing calculation code: {str(e)}")
        raise


def validate_filter_code(code_str: str) -> bool:
    """
    Validates the generated filter code meets requirements.

    Args:
        code_str (str): The generated Python code

    Returns:
        bool: True if code is valid, False otherwise
    """
    # Check if code defines filter_products function
    if "def filter_products" not in code_str:
        Logger(__name__, LoggerType.SLS).error("Missing filter_products function definition")
        return False

    # Check for test data generation
    if "example data" in code_str.lower() or "test data" in code_str.lower():
        Logger(__name__, LoggerType.SLS).error("Code contains example/test data")
        return False

    # Basic syntax check
    try:
        compile(code_str, '<string>', 'exec')
    except SyntaxError as e:
        Logger(__name__, LoggerType.SLS).error(f"Syntax error in generated code: {str(e)}")
        return False

    return True


def validate_calculation_code(code_str: str) -> bool:
    """
    Validates the generated filter code meets requirements.

    Args:
        code_str (str): The generated Python code

    Returns:
        bool: True if code is valid, False otherwise
    """
    # Check if code defines filter_products function
    if "def calculate_indicator" not in code_str:
        Logger(__name__, LoggerType.SLS).error("Missing calculate_indicator function definition")
        return False

    # Check for test data generation
    if "example data" in code_str.lower() or "test data" in code_str.lower():
        Logger(__name__, LoggerType.SLS).error("Code contains example/test data")
        return False

    # Basic syntax check
    try:
        compile(code_str, '<string>', 'exec')
    except SyntaxError as e:
        Logger(__name__, LoggerType.SLS).error(f"Syntax error in generated code: {str(e)}")
        return False

    return True


# def get_mutual_fund_NV() -> float:
#     """
#     Get the net asset value (NAV) of a mutual fund.
#     """
#     sql = f"""
#     SELECT  tradingday --交易日期
#             ,symbol --基金code
#             ,real_date --真实日期
#             ,fund_name_abbr --基金名
#             ,fund_type --基金类型 INDEX BLEND STOCK
#             ,restored_net_value -- 基金复权之后的累计净值
#     FROM    antefi.re_b_fund_wide_table_ds
#     WHERE   dt = MAX_PT('antefi.re_b_fund_wide_table_ds')
#     AND     fund_type NOT IN ('BOND');
#     """
#     # 查询数据
#     mutual_fund_NV_result = UniversalODPSOperator.execute_sql(sql)
#     return mutual_fund_NV_result

def get_mutual_fund_NV(start_date, end_date) -> float:
    """
    Get the net asset value (NAV) of a mutual fund.
    """
    fund_code_sql = f'''
                        select distinct fund_code as symbol, product_id  from antefi.ods_fund_archive
                        WHERE dt = MAX_PT('antefi.ods_fund_archive')
                    '''
    fund_df = UniversalODPSOperator.execute_sql(fund_code_sql)

    pfund_list_sql = "select fund_code as symbol, product_id from efiods.ods_fp_private where dt = max_pt('efiods.ods_fp_private')"
    pfund_df = UniversalODPSOperator.execute_sql(pfund_list_sql)

    merge_df = pd.concat([fund_df, pfund_df], sort=False)
    merge_df = merge_df.drop_duplicates()
    filter = merge_df['symbol'].unique().tolist()[:1000]  # todo 临时演示 只取前1000只基金
    # 添加 .OF 后缀
    filter = [f"{i}.OF" for i in filter]

    dfd_data = dfd_client.query_fact(
        # data_id="quotresearch_fund_quotation",
        data_id="quotresearch_fund_multi_net_value",
        tags={
            'symbol': filter,
        },
        fields=['net_value_date', 'symbol', 'restored_net_value'],
        start=start_date,
        end=end_date,
        db_mode="sim",
        token="fap.antalpha.2A"
    )
    # 去除后缀
    dfd_data['symbol'] = dfd_data['symbol'].apply(lambda x: x.split('.')[0])
    dfd_data = dfd_data.rename(columns={'net_value_date': 'the_datetime', 'restored_net_value': 'value'})
    return dfd_data


def query_nscode_by_metadata(target_str):
    sql = f'''
    select ns_code, chi_name, name, domain_type, asset_type 
    from fap_onecode_factor
    where chi_name like '%{target_str}%'
    and asset_type not in ('PRIVATE_FUND', 'SPECIAL_ACCOUNT')
    '''
    target = UniversalOBOperator.execute_sql(sql, source=OBSource.FAP)
    return target


def get_metadata_str(ns_code):
    rename_dict = {'FUND': '公募基金', 'INDEX': '行业指数', 'STOCK': '股票'}

    sql = f'''
    select chi_name, name, domain_type, asset_type, ns_code 
    from fap_onecode_factor
    where ns_code = '{ns_code}'
    '''
    print(f'obproxy={UniversalOBOperator.use_ob_proxy}')
    target = UniversalOBOperator.execute_sql(sql)

    # 转译
    target['asset_type'] = target['asset_type'].replace(rename_dict)

    if len(target) == 0:
        return ''
    else:
        return target['asset_type'].values[0] + '_' + target['chi_name'].values[0]


# 简单因子
def quote_alpha_simple_factor_ns(nscode, filter, period=['1d'], frequency=['day'], d0='2000-01-01 00:00:00',
                                 d1='2099-01-01 00:00:00', brief=True):
    # todo: filter可为空，传一个范围
    if filter is None or filter == []:
        fund_code_sql = f'''
                            select distinct fund_code as symbol, product_id  from antefi.ods_fund_archive
                            WHERE dt = MAX_PT('antefi.ods_fund_archive')
                        '''
        fund_df = UniversalODPSOperator.execute_sql(fund_code_sql)

        pfund_list_sql = "select fund_code as symbol, product_id from efiods.ods_fp_private where dt = max_pt('efiods.ods_fp_private')"
        pfund_df = UniversalODPSOperator.execute_sql(pfund_list_sql)

        merge_df = pd.concat([fund_df, pfund_df], sort=False)
        merge_df = merge_df.drop_duplicates()
        filter = merge_df['symbol'].unique().tolist()[:10]  # todo 临时演示 只取前1000只基金

    if brief:
        dat = DfDatapSDKOperatorQE.sdk_query_domain_series(ns_code=nscode,
                                                           filters={"symbol": filter, 'frequency': frequency,
                                                                    'period': period},
                                                           key='the_datetime',
                                                           start=d0,
                                                           end=d1,
                                                           slot_num=1,
                                                           db_mode='sim'
                                                           )
    else:
        dat = DfDatapSDKOperatorQE.sdk_query_domain_series(ns_code=nscode,
                                                           filters={"symbol": filter, 'frequency': frequency,
                                                                    'period': period},
                                                           key='the_datetime',
                                                           start=d0,
                                                           end=d1,
                                                           db_mode='sim'
                                                           )

    # 拼接元信息
    dat['ext_props'] = get_metadata_str(nscode)
    dat['ext_props'] = dat['ext_props'] + '_' + dat['period'] + '_' + dat['frequency']
    dat['p_datetime'] = dat['the_datetime']
    return dat[['symbol', 'the_datetime', 'p_datetime', 'value', 'ext_props']].sort_values(by='the_datetime',
                                                                                           ascending=True)


# 简单因子排名 - ALPHA_SIMPLE_FACTOR_RANK
def quote_alpha_simple_factor_rank_ns(nscode, filter, period=['1d'], frequency=['day'],
                                      rankscope=['TxAfterClassifyType'], d0='2000-01-01 00:00:00',
                                      d1='2099-01-01 00:00:00', brief=True):
    # todo: filter可为空，传一个范围
    if brief:
        dat = DfDatapSDKOperatorQE.sdk_query_domain_series(ns_code=nscode,
                                                           filters={"symbol": filter, 'frequency': frequency,
                                                                    'perio d': period, 'rank_scope': rankscope},
                                                           key='the_datetime',
                                                           start=d0,
                                                           end=d1,
                                                           slot_num=1,
                                                           db_mode='sim'
                                                           )
    else:
        dat = DfDatapSDKOperatorQE.sdk_query_domain_series(ns_code=nscode,
                                                           filters={"symbol": filter, 'frequency': frequency,
                                                                    'period': period, 'rank_scope': rankscope},
                                                           key='the_datetime',
                                                           start=d0,
                                                           end=d1,
                                                           db_mode='sim'
                                                           )

    # 拼接元信息
    dat['ext_props'] = get_metadata_str(nscode)
    dat['ext_props'] = dat['ext_props'] + '_' + dat['period'] + '_' + dat['frequency'] + '_' + dat['rank_scope']
    dat['p_datetime'] = dat['the_datetime']

    # 取排名值作为value字段
    dat = dat.rename(columns={'rank_pct': 'value'})
    return dat[['symbol', 'the_datetime', 'p_datetime', 'value', 'ext_props']].sort_values(by='the_datetime',
                                                                                           ascending=True)


# 统计因子
def quote_alpha_stat_factor_ns(nscode, filter, period=['1d'], frequency=['day'], hold_period=['1m'],
                               d0='2000-01-01 00:00:00', d1='2099-01-01 00:00:00', brief=True):
    # todo: filter可为空，传一个范围

    if brief:
        dat = DfDatapSDKOperatorQE.sdk_query_domain_series(ns_code=nscode,
                                                           filters={"symbol": filter, 'frequency': frequency,
                                                                    'period': period, 'holding_period': hold_period},
                                                           key='the_datetime',
                                                           start=d0,
                                                           end=d1,
                                                           slot_num=1,
                                                           db_mode='sim'
                                                           )
    else:
        dat = DfDatapSDKOperatorQE.sdk_query_domain_series(ns_code=nscode,
                                                           filters={"symbol": filter, 'frequency': frequency,
                                                                    'period': period, 'holding_period': hold_period},
                                                           key='the_datetime',
                                                           start=d0,
                                                           end=d1,
                                                           db_mode='sim'
                                                           )

    # 拼接元信息
    dat['ext_props'] = get_metadata_str(nscode)
    dat['ext_props'] = dat['ext_props'] + '_' + dat['period'] + '_' + dat['frequency'] + '_持有' + dat['holding_period']

    dat['p_datetime'] = dat['the_datetime']
    return dat[['symbol', 'the_datetime', 'p_datetime', 'value', 'ext_props']].sort_values(by='the_datetime',
                                                                                           ascending=True)


# 跟踪统计因子
def quote_alpha_track_stat_factor_ns(nscode, filter, period=['1d'], frequency=['day'], hold_period=['1m'],
                                     track_target=['000300'], d0='2000-01-01 00:00:00', d1='2099-01-01 00:00:00',
                                     brief=True):
    # todo: filter可为空，传一个范围

    if brief:
        dat = DfDatapSDKOperatorQE.sdk_query_domain_series(ns_code=nscode,
                                                           filters={"symbol": filter, 'frequency': frequency,
                                                                    'period': period, 'holding_period': hold_period,
                                                                    'tracking_target': track_target},
                                                           key='the_datetime',
                                                           start=d0,
                                                           end=d1,
                                                           slot_num=1,
                                                           db_mode='sim'
                                                           )
    else:
        dat = DfDatapSDKOperatorQE.sdk_query_domain_series(ns_code=nscode,
                                                           filters={"symbol": filter, 'frequency': frequency,
                                                                    'period': period, 'holding_period': hold_period,
                                                                    'tracking_target': track_target},
                                                           key='the_datetime',
                                                           start=d0,
                                                           end=d1,
                                                           db_mode='sim'
                                                           )

    # 拼接元信息
    dat['ext_props'] = get_metadata_str(nscode)
    dat['ext_props'] = dat['ext_props'] + '_' + dat['period'] + '_' + dat['frequency'] + '_持有' + dat[
        'holding_period'] + '_相对' + dat['tracking_target']

    dat['p_datetime'] = dat['the_datetime']
    return dat[['symbol', 'the_datetime', 'p_datetime', 'value', 'ext_props']].sort_values(by='the_datetime',
                                                                                           ascending=True)


if __name__ == '__main__':
    from agentuniverse_ant_ext.connector.oceanbase.universal_ob_operator import UniversalOBOperator
    from agentuniverse_ant_ext.connector.oceanbase.ob_source import OBSource
    from agentuniverse.base.agentuniverse import AgentUniverse

    AgentUniverse().start(config_path='../../../../config/config.toml')
    #
    # sql = f"""--  select * from zxz_cloud_service_instance limit 20"""
    # df = UniversalOBOperator.execute_sql(sql, source=OBSource.FAP_QUANT_HUB)
    #
    # sql = f""" select * from fap_onecode_factor limit 20 """
    # df = UniversalOBOperator.execute_sql(sql, source=OBSource.FAP)
    # print(df)

    Logger(__name__, LoggerType.SLS).info('test quote_alpha_simple_factor_ns')
    # data = quote_alpha_simple_factor_ns(nscode='fund.indicator.annual_returns',
    #                                     filter=['000001', '000017'],
    #                                     period=['1y'],
    #                                     frequency=['day'],
    #                                     d0='2024-01-01 00:00:00',
    #                                     d1='2099-01-01 00:00:00',
    #                                     brief=False)
    # print(data)

    dfd_data = quote_alpha_simple_factor_ns(
        nscode='fund.indicator.max_drawdown',
        filter=None,
        period=['1y'],
        frequency=['day'],
        d0='2024-01-01 00:00:00',
        d1='2099-01-01 00:00:00',
        brief=True)
    print(dfd_data)

    # data = quote_alpha_simple_factor_ns(nscode='fund.indicator.annual_returns',
    #                                     filter=None,  # 传None，默认查询所有公募基金
    #                                     period=['1y'],
    #                                     frequency=['day'],
    #                                     d0='2024-01-01 00:00:00',
    #                                     d1='2099-01-01 00:00:00',
    #                                     brief=True)
    # print(data)



