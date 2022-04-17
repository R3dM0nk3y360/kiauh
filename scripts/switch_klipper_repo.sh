#!/bin/bash

#=======================================================================#
# Copyright (C) 2020 - 2022 Dominik Willner <th33xitus@gmail.com>       #
#                                                                       #
# This file is part of KIAUH - Klipper Installation And Update Helper   #
# https://github.com/th33xitus/kiauh                                    #
#                                                                       #
# This file may be distributed under the terms of the GNU GPLv3 license #
#=======================================================================#

set -e

function change_klipper_repo_menu(){
  local repo_file="${SRCDIR}/kiauh/klipper_repos.txt"
  local url branch

  top_border
  echo -e "|     ~~~~~~~~ [ Set custom Klipper repo ] ~~~~~~~~     | "
  hr
  blank_line
  ### dynamically generate the repolist from the klipper_repos.txt textfile
  get_klipper_repo_list "${repo_file}"
  blank_line
  back_help_footer

  while IFS="," read -r col1 col2; do
    url+=("${col1}")
    branch+=("${col2}")
  done < <(grep "" "${repo_file}" | tail -n "+11")

  while true; do
    read -p "${cyan}Perform action:${white} " option
    case "${option}" in
      0 | "$((option < ${#url[@]}))")
        if [ -d "${KLIPPER_DIR}" ]; then
          top_border
          echo -e "|                   ${red}!!! ATTENTION !!!${white}                   |"
          echo -e "| Existing Klipper folder found! Proceeding will remove | "
          echo -e "| the existing Klipper folder and replace it with a     | "
          echo -e "| clean copy of the previously selected source repo!    | "
          bottom_border
          while true; do
          read -p "${cyan}###### Proceed? (Y/n):${white} " yn
            case "${yn}" in
              Y|y|Yes|yes|"")
                select_msg "Yes"
                switch_klipper_repo "${url[${option}]}" "${branch[${option}]}"
                set_custom_klipper_repo "${url[${option}]}" "${branch[${option}]}"
                break;;
              N|n|No|no)
                select_msg "No"
                break;;
              *)
              error_msg "Invalid command!";;
            esac
          done
        else
          status_msg "Set custom Klipper repository to:\n       ● Repository URL: ${url[${option}]}\n       ● Branch: ${branch[${option}]}"
          set_custom_klipper_repo "${url[${option}]}" "${branch[${option}]}"
          ok_msg "This repo will now be used for new Klipper installations!\n"
        fi
        break;;
      B|b)
        clear && print_header
        settings_menu
        break;;
      H|h)
        clear && print_header
        show_custom_klipper_repo_help
        break;;
      *)
        error_msg "Invalid command!";;
    esac
  done
}

#================================================#
#=================== HELPERS ====================#
#================================================#

function get_klipper_repo_list(){
  local repo_file=${1} i=0
  while IFS="," read -r col1 col2; do
    col1=$(echo "${col1}" | sed "s/https:\/\/github\.com\///" | sed "s/\.git$//" )
    col1=${yellow}${col1}${white}
    printf "| ${i}) %s → %-31s|\n" "${col1}" "${col2}"
    i=$((i+1))
  done < <(grep "" "${repo_file}" | tail -n "+11")
}

function switch_klipper_repo(){
  local url branch
  url=${1} branch=${2}
  status_msg "Switching Klipper repository..."
  do_action_service "stop" "klipper"
  cd "${HOME}"
  [ -d "${KLIPPER_DIR}" ] && rm -rf "${KLIPPER_DIR}"
  git clone "${url}" "klipper" && cd "${KLIPPER_DIR}"
  git checkout "${branch}" && cd "${HOME}"
  do_action_service "start" "klipper"
}

function show_custom_klipper_repo_help(){
  top_border
  echo -e "|   ~~~~ < ? > Help: Custom Klipper repo < ? > ~~~~     |"
  hr
  echo -e "| With this setting, it is possible to install Klipper  | "
  echo -e "| from a custom repository. It will also switch an      | "
  echo -e "| existing Klipper installation to the newly selected   | "
  echo -e "| source repository.                                    | "
  echo -e "| A list of selectable repositories is automatically    | "
  echo -e "| generated by a 'klipper_repos.txt' textfile in KIAUHs | "
  echo -e "| root folder. You can add as many additional repos as  | "
  echo -e "| you wish. Make sure to always add URL ${red}and${white} branch!     | "
  blank_line
  back_footer
  while true; do
    read -p "${cyan}###### Please select:${white} " choice
    case "${choice}" in
      B|b)
        clear && print_header
        change_klipper_repo_menu
        break;;
      *)
        deny_action "show_settings_help";;
    esac
  done
}