#!/usr/bin/env python3

# ======================================================================= #
#  Copyright (C) 2020 - 2024 Dominik Willner <th33xitus@gmail.com>        #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #

import shutil
import subprocess
from pathlib import Path
from typing import List, get_args, Union, Set

from kiauh import KIAUH_CFG
from components.klipper.klipper import Klipper
from components.moonraker.moonraker import Moonraker
from components.webui_client import ClientConfigData, ClientName, ClientData
from components.webui_client.client_dialogs import print_client_already_installed_dialog
from components.webui_client.client_utils import (
    load_client_data,
    backup_client_config_data,
)
from core.config_manager.config_manager import ConfigManager

from core.instance_manager.instance_manager import InstanceManager
from core.repo_manager.repo_manager import RepoManager
from utils.filesystem_utils import (
    create_symlink,
    add_config_section,
)
from utils.input_utils import get_confirm
from utils.logger import Logger


def install_client_config(client_name: ClientName) -> None:
    client: ClientData = load_client_data(client_name)
    client_config: ClientConfigData = client.get("client_config")
    d_name = client_config.get("display_name")

    if config_for_other_client_exist(client_name):
        Logger.print_info("Another Client-Config is already installed! Skipped ...")
        return

    if client_config.get("dir").exists():
        print_client_already_installed_dialog(d_name)
        if get_confirm(f"Re-install {d_name}?", allow_go_back=True):
            shutil.rmtree(client_config.get("dir"))
        else:
            return

    mr_im = InstanceManager(Moonraker)
    mr_instances: List[Moonraker] = mr_im.instances
    kl_im = InstanceManager(Klipper)
    kl_instances = kl_im.instances

    try:
        download_client_config(client_config)
        create_client_config_symlink(client_config, kl_instances)
        add_config_section(
            section=f"update_manager {client_config.get('name')}",
            instances=mr_instances,
            options=[
                ("type", "git_repo"),
                ("primary_branch", "master"),
                ("path", client_config.get("mr_conf_path")),
                ("origin", client_config.get("mr_conf_origin")),
                ("managed_services", "klipper"),
            ],
        )
        add_config_section(client_config.get("printer_cfg_section"), kl_instances)
        kl_im.restart_all_instance()

    except Exception as e:
        Logger.print_error(f"{d_name} installation failed!\n{e}")
        return

    Logger.print_ok(f"{d_name} installation complete!", start="\n")


def config_for_other_client_exist(client_to_ignore: ClientName) -> bool:
    """
    Check if any other client configs are present on the system.
    It is usually not harmful, but chances are they can conflict each other.
    Multiple client configs are, at least, redundant to have them installed
    :param client_to_ignore: The client name to ignore for the check
    :return: True, if other client configs were found, else False
    """

    clients = set([c["name"] for c in get_existing_client_config()])
    clients = clients - {client_to_ignore}

    return True if len(clients) > 0 else False


def get_existing_clients() -> List[ClientData]:
    clients = list(get_args(ClientName))
    installed_clients: List[ClientData] = []
    for c in clients:
        c_data: ClientData = load_client_data(c)
        if c_data.get("dir").exists():
            installed_clients.append(c_data)

    return installed_clients


def get_existing_client_config() -> List[ClientData]:
    clients = list(get_args(ClientName))
    installed_client_configs: List[ClientData] = []
    for c in clients:
        c_data: ClientData = load_client_data(c)
        c_config_data: ClientConfigData = c_data.get("client_config")
        if c_config_data.get("dir").exists():
            installed_client_configs.append(c_data)

    return installed_client_configs


def download_client_config(client_config: ClientConfigData) -> None:
    try:
        Logger.print_status(f"Downloading {client_config.get('display_name')} ...")
        rm = RepoManager(
            client_config.get("url"), target_dir=str(client_config.get("dir"))
        )
        rm.clone_repo()
    except Exception:
        Logger.print_error(f"Downloading {client_config.get('display_name')} failed!")
        raise


def update_client_config(client: ClientData) -> None:
    client_config: ClientConfigData = client.get("client_config")

    Logger.print_status(f"Updating {client_config.get('display_name')} ...")

    cm = ConfigManager(cfg_file=KIAUH_CFG)
    if cm.get_value("kiauh", "backup_before_update"):
        backup_client_config_data(client)

    repo_manager = RepoManager(
        repo=client_config.get("url"),
        branch="master",
        target_dir=str(client_config.get("dir")),
    )
    repo_manager.pull_repo()

    Logger.print_ok(f"Successfully updated {client_config.get('display_name')}.")
    Logger.print_warn("Remember to restart Klipper to reload the configurations!")


def create_client_config_symlink(
    client_config: ClientConfigData, klipper_instances: List[Klipper] = None
) -> None:
    if klipper_instances is None:
        kl_im = InstanceManager(Klipper)
        klipper_instances = kl_im.instances

    Logger.print_status(f"Create symlink for {client_config.get('cfg_filename')} ...")
    source = Path(client_config.get("dir"), client_config.get("cfg_filename"))
    for instance in klipper_instances:
        target = instance.cfg_dir
        Logger.print_status(f"Linking {source} to {target}")
        try:
            create_symlink(source, target)
        except subprocess.CalledProcessError:
            Logger.print_error("Creating symlink failed!")
