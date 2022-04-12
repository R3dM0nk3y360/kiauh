update_log_paths(){
  ### update services to make use of moonrakers new log_path option
  ### https://github.com/Arksine/moonraker/commit/829b3a4ee80579af35dd64a37ccc092a1f67682a
  shopt -s extglob # enable extended globbing
  source_kiauh_ini
  LPATH="${HOME}/klipper_logs"
  [ ! -d "$LPATH" ] && mkdir -p "$LPATH"
  FILE="$SYSTEMDDIR/$1?(-*([0-9])).service"
  for file in $(ls $FILE); do
    [ "$1" == "klipper" ] && LOG="klippy"
    [ "$1" == "moonraker" ] && LOG="moonraker"
    if [ ! "$(grep "\-l" $file)" ]; then
      status_msg "Updating $file ..."
      sudo sed -i -r "/ExecStart=/ s|$| -l $LPATH/$LOG.log|" $file
      ok_msg "$file updated!"
    elif [ "$(grep "\-l \/tmp\/$LOG" $file)" ]; then
      status_msg "Updating $file ..."
      sudo sed -i -r "/ExecStart=/ s|-l \/tmp\/$LOG|-l $LPATH/$LOG|" $file
      ok_msg "$file updated!"
    fi
  done
  sudo systemctl daemon-reload

  # patch log_path entry if not found
  dir1="$klipper_cfg_loc"
  dir2="$klipper_cfg_loc/printer_*"
  for conf in $(find $dir1 $dir2 -name "moonraker.conf" 2> /dev/null); do
    if ! grep -q "log_path" $conf; then
      status_msg "Patching $conf"
      sed -i "/^config_path/a log_path: $LPATH" $conf
      ok_msg "OK!"
    fi
  done

  # create symlink for mainsail and fluidd nginx logs
  symlink_webui_nginx_log "mainsail"
  symlink_webui_nginx_log "fluidd"

  # create symlink for webcamd log
  if [ -f "/var/log/webcamd.log" ] && [ ! -L "$LPATH/webcamd.log" ]; then
    status_msg "Creating symlink for '/var/log/webcamd.log' ..."
    ln -s "/var/log/webcamd.log" "$LPATH"
    ok_msg "OK!"
  fi

  shopt -u extglob # disable extended globbing
}

update_system(){
  status_msg "Updating System ..."
  sudo apt-get update --allow-releaseinfo-change && sudo apt-get upgrade -y
  CONFIRM_MSG="Update complete! Check the log above!\n ${yellow}KIAUH will not install any dist-upgrades or\n any packages which have been kept back!${green}"
  print_msg && clear_msg
}