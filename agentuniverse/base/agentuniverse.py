# !/usr/bin/env python3
# -*- coding:utf-8 -*-

# @Time    : 2024/4/2 15:27
# @Author  : jerry.zzw 
# @Email   : jerry.zzw@antgroup.com
# @FileName: agentuniverse.py
import importlib
import sys
from pathlib import Path

from agentuniverse.base.annotation.singleton import singleton
from agentuniverse.base.component.application_component_manager import ApplicationComponentManager
from agentuniverse.base.component.component_base import ComponentBase
from agentuniverse.base.config.application_configer.app_configer import AppConfiger
from agentuniverse.base.config.application_configer.application_config_manager import ApplicationConfigManager
from agentuniverse.base.config.component_configer.component_configer import ComponentConfiger
from agentuniverse.base.component.component_configer_util import ComponentConfigerUtil
from agentuniverse.base.config.config_type_enum import ConfigTypeEnum
from agentuniverse.base.config.configer import Configer
from agentuniverse.base.config.custom_configer.custom_key_configer import CustomKeyConfiger
from agentuniverse.base.component.component_enum import ComponentEnum
from agentuniverse.base.util.system_util import get_project_root_path
from agentuniverse.base.util.logging.logging_util import init_loggers
from agentuniverse.agent_serve.web.request_task import RequestLibrary
from agentuniverse.agent_serve.web.web_booster import GunicornApplication


@singleton
class AgentUniverse(object):
    """agentUniverse object, responsible for the framework initialization,
       system variables management, etc."""

    def __init__(self):
        self.__application_container = ApplicationComponentManager()
        self.__config_container: ApplicationConfigManager = ApplicationConfigManager()
        self.__system_default_package = ['agentuniverse']

    def start(self, config_path: str = None):
        """Start the agentUniverse framework."""
        # step0: get default config path
        project_root_path = get_project_root_path()
        app_path = project_root_path / 'app'
        if app_path.exists():
            sys.path.append(str(app_path))
        if not config_path:
            config_path = project_root_path / 'config' / 'config.toml'
            config_path = str(config_path)

        # step1: load the configuration file
        configer = Configer(path=config_path).load()
        app_configer = AppConfiger().load_by_configer(configer)
        self.__config_container.app_configer = app_configer

        # Load User custom key.
        custom_key_configer_path = self.__parse_sub_config_path(
            configer.value.get('SUB_CONFIG_PATH', {}).get('custom_key_path'),
            config_path)
        CustomKeyConfiger(custom_key_configer_path)

        # Init loguru loggers.
        log_config_path = self.__parse_sub_config_path(
            configer.value.get('SUB_CONFIG_PATH', {}).get('log_config_path'),
            config_path)
        init_loggers(log_config_path)

        # Init web request task database.
        RequestLibrary(configer=configer)

        # Init gunicorn web server.
        gunicorn_config_path = self.__parse_sub_config_path(
            configer.value.get('SUB_CONFIG_PATH', {})
            .get('gunicorn_config_path'), config_path)
        GunicornApplication(config_path=gunicorn_config_path)

        # step2: scan and register the components
        self.__scan_and_register(self.__config_container.app_configer)

    def __scan_and_register(self, app_configer: AppConfiger):
        """Scan the component directory and register the components.

        Args:
            app_configer(AppConfiger): the AppConfiger object
        """
        core_agent_package_list = app_configer.core_agent_package_list or app_configer.core_default_package_list + self.__system_default_package
        core_knowledge_package_list = app_configer.core_knowledge_package_list or app_configer.core_default_package_list + self.__system_default_package
        core_llm_package_list = app_configer.core_llm_package_list or app_configer.core_default_package_list + self.__system_default_package
        core_planner_package_list = app_configer.core_planner_package_list or app_configer.core_default_package_list + self.__system_default_package
        core_tool_package_list = app_configer.core_tool_package_list or app_configer.core_default_package_list + self.__system_default_package
        core_service_package_list = app_configer.core_service_package_list or app_configer.core_default_package_list + self.__system_default_package
        core_memory_package_list = app_configer.core_memory_package_list or app_configer.core_default_package_list + self.__system_default_package

        component_package_map = {
            ComponentEnum.AGENT: core_agent_package_list,
            ComponentEnum.KNOWLEDGE: core_knowledge_package_list,
            ComponentEnum.LLM: core_llm_package_list,
            ComponentEnum.PLANNER: core_planner_package_list,
            ComponentEnum.TOOL: core_tool_package_list,
            ComponentEnum.SERVICE: core_service_package_list,
            ComponentEnum.MEMORY: core_memory_package_list
        }

        component_configer_list_map = {}
        for component_enum, package_list in component_package_map.items():
            if not package_list:
                continue
            component_configer_list = self.__scan(package_list, ConfigTypeEnum.YAML, component_enum)
            component_configer_list_map[component_enum] = component_configer_list

        for component_enum, component_configer_list in component_configer_list_map.items():
            self.__register(component_enum, component_configer_list)

    def __scan(self,
               package_list: [str],
               config_type_enum: ConfigTypeEnum,
               component_enum: ComponentEnum) -> list:
        """Scan the component directory and return certain component configer list.

        Args:
            package_list(list): the package list
            config_type_enum(ConfigTypeEnum): the configuration file type enumeration
            component_enum(ComponentEnum): the component enumeration

        Returns:
            list: the component configer list
        """
        component_configer_list = []
        for package_name in package_list:
            package_path = self.__package_name_to_path(package_name)
            path = Path(package_path)
            config_files = path.rglob(f'*.{config_type_enum.value}')
            for config_file in config_files:
                config_file_str = str(config_file)
                configer = Configer(path=config_file_str).load()
                component_configer = ComponentConfiger().load_by_configer(configer)
                component_config_type = component_configer.get_component_config_type()
                if component_config_type == component_enum.value:
                    component_configer_list.append(component_configer)
        return component_configer_list

    def __register(self, component_enum: ComponentEnum, component_configer_list: list[ComponentConfiger]):
        """Register the components.

        Args:
            component_enum(ComponentEnum): the component enumeration
            component_configer_list(list): the component configer list
        """
        component_manager_clz = ComponentConfigerUtil.get_component_manager_clz_by_type(component_enum)
        for component_configer in component_configer_list:
            configer_clz = ComponentConfigerUtil.get_component_config_clz_by_type(component_enum)
            configer_instance: ComponentConfiger = configer_clz().load_by_configer(component_configer.configer)
            component_clz = ComponentConfigerUtil.get_component_object_clz_by_component_configer(configer_instance)
            component_instance: ComponentBase = component_clz().initialize_by_component_configer(configer_instance)
            if component_instance is None:
                continue
            component_manager_clz().register(component_instance.get_instance_code(), component_instance)

    def __package_name_to_path(self, package_name: str) -> str:
        """Convert the package name to the package path.

        Args:
            package_name(str): the package name

        Returns:
            str: the package path
        """
        # get the package spec
        spec = importlib.util.find_spec(package_name)
        if spec is None:
            raise ImportError(f"Can not find {package_name}")
        # get the package path
        package_path = spec.submodule_search_locations[0] if spec.submodule_search_locations else spec.origin
        return package_path

    def __parse_sub_config_path(self, input_path: str,
                                reference_file_path: str) -> str | None:
        """Resolve a sub config file path according to main config file.

            Args:
                input_path(str): Absolute or relative path of sub config file.
                reference_file_path(str): Main config file path.
            Returns:
                str or None: Final
        """
        if not input_path:
            return None

        input_path_obj = Path(input_path)
        if input_path_obj.is_absolute():
            combined_path = input_path_obj
        else:
            reference_file_path_obj = Path(reference_file_path)
            combined_path = reference_file_path_obj.parent / input_path_obj

        return str(combined_path)
