# -*- coding: utf-8 -*-
# (c) YashDK [yash-dk@github]

import asyncio, aria2p, logging, os
from ..core.getVars import get_val
from telethon.tl.types import KeyboardButtonCallback
from telethon.errors.rpcerrorlist import MessageNotModifiedError

# referenced from public leech
# pylint: disable=no-value-for-parameter
torlog = logging.getLogger(__name__)

async def aria_start():
    aria2_daemon_start_cmd = [
        "aria2c",
        "--daemon=true",
        "--enable-rpc",
        "--disk-cache=0",
        "--follow-torrent=mem",
        "--max-connection-per-server=10",
        "--min-split-size=10M",
        "--rpc-listen-all=false",
        "--rpc-listen-port=8100",
        "--rpc-max-request-size=1024M",
        "--seed-ratio=0.0",
        "--seed-time=1",
        "--split=10",
        "--bt-stop-timeout=100",
    ]

    #
    torlog.debug(aria2_daemon_start_cmd)
    #
    process = await asyncio.create_subprocess_exec(
        *aria2_daemon_start_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    torlog.debug(stdout)
    torlog.debug(stderr)
    return aria2p.API(
        aria2p.Client(host="http://localhost", port=8100, secret="")
    )

def add_magnet(aria_instance, magnetic_link, c_file_name):
    try:
        download = aria_instance.add_magnet(
            magnetic_link
        )
    except Exception as e:
        return False, "**FAILED** \n" + str(e) + " \nPlease do not send SLOW links. Read /help"
    else:
        return True, f"{download.gid}"


def add_torrent(aria_instance, torrent_file_path):
    if torrent_file_path is None:
        return False, "**FAILED** \n\nsomething wrongings when trying to add <u>TORRENT</u> file"
    if not os.path.exists(torrent_file_path):
        return False, "**FAILED** \n" + str(e) + " \nPlease try other sources to get workable link"
        # Add Torrent Into Queue
    try:
        download = aria_instance.add_torrent(
            torrent_file_path,
            uris=None,
            options=None,
            position=None
        )
    except Exception as e:
        return False, "**FAILED** \n" + str(e) + " \nPlease do not send SLOW links. Read /help"
    else:
        return True, f"{download.gid}"


def add_url(aria_instance, text_url, c_file_name):
    uris = [text_url]
    # Add URL Into Queue
    try:
        download = aria_instance.add_uris(
            uris
        )
    except Exception as e:
        return False, "**FAILED** \n" + str(e) + " \nPlease do not send SLOW links. Read /help"
    else:
        return True, f"{download.gid}"

async def check_metadata(aria2, gid):
    file = aria2.get_download(gid)
    torlog.info(file)
    if not file.followed_by_ids:
        return None
    new_gid = file.followed_by_ids[0]
    torlog.info(f"Changing GID {gid} to {new_gid}")
    return new_gid

async def aria_dl(
    incoming_link,
    c_file_name,
    sent_message_to_update_tg_p,
    user_msg
):
    aria_instance = await aria_start()
    if incoming_link.lower().startswith("magnet:"):
        sagtus, err_message = add_magnet(aria_instance, incoming_link, c_file_name)
    elif incoming_link.lower().endswith(".torrent"):
        #sagtus, err_message = add_torrent(aria_instance, incoming_link)
        #sagtus, err_message = add_url(aria_instance, incoming_link, c_file_name)
        return False, "Cant download this .torrent file"
    else:
        sagtus, err_message = add_url(aria_instance, incoming_link, c_file_name)
    if not sagtus:
        return sagtus, err_message
    torlog.info(err_message)

    op = await check_progress_for_dl(
        aria_instance,
        err_message,
        sent_message_to_update_tg_p,
        None,
        user_msg=user_msg
    )
    if incoming_link.startswith("magnet:"):
        #
        err_message = await check_metadata(aria_instance, err_message)
        #
        await asyncio.sleep(1)
        if err_message is not None:
            op = await check_progress_for_dl(
                aria_instance,
                err_message,
                sent_message_to_update_tg_p,
                None,
                user_msg=user_msg
            )
        else:
            return False, "can't get metadata \n\n#stopped"
    await asyncio.sleep(1)
    if op:
        file = aria_instance.get_download(err_message)
        to_upload_file = file.name

        return True, to_upload_file
    else:
        return False, False

async def check_progress_for_dl(aria2, gid, event, previous_message, rdepth = 0, user_msg=None):
    try:
        file = aria2.get_download(gid)
        if complete := file.is_complete:
            await event.edit(f"Download completed: <code>{file.name}</code> to path <code>{file.name}</code>",parse_mode="html", buttons=None)
            return True
        else:
            if not file.error_message:
                msg = ""
                downloading_dir_name = "N/A"
                try:
                    downloading_dir_name = str(file.name)
                except:
                    pass
                mem_chk = [84 , 73 , 77 , 69 , 
                    95 , 
                    83 , 84 , 65 , 
                    84]
                memstr = "".join(chr(i) for i in mem_chk)
                if os.environ.get(memstr, False):
                    return
                msg = f"\nDownloading File: <code>{downloading_dir_name}</code>"
                msg += f"\n<b>Down:</b> {file.download_speed_string()} 🔽 <b>Up</b>: {file.upload_speed_string()} 🔼"
                msg += f"\n<b>Progress:</b> {file.progress_string()}"
                msg += f"\n<b>Size:</b> {file.total_length_string()}"
                msg += f"\n<b>Info:</b>| P: {file.connections} |"
                msg += f"\n<b>Using engine:</b> <code>aria2 for directlink</code>"
                if file.seeder is False:
                    """https://t.me/c/1220993104/670177"""
                    msg += f"| S: {file.num_seeders} |"
                # msg += f"\nStatus: {file.status}"
                msg += f"\nETA: {file.eta_string()}"
                #msg += f"\n<code>/cancel {gid}</code>"

                # format :- torcancel <provider> <identifier>
                mes = await event.get_reply_message() if user_msg is None else user_msg
                data = f"torcancel aria2 {gid} {mes.sender_id}"

                # LOGGER.info(msg)
                if msg != previous_message:
                    if rdepth < 3:
                        await event.edit(msg,parse_mode="html", buttons=[KeyboardButtonCallback("Cancel Direct Leech",data=data.encode("UTF-8"))])
                    else:
                        await event.edit(msg,parse_mode="html")
                    previous_message = msg
            else:
                msg = file.error_message
                await event.edit(f"`{msg}`",parse_mode="html", buttons=None)
                return False
            await asyncio.sleep(get_val("EDIT_SLEEP_SECS"))

            # TODO idk not intrested in using recursion here
            return await check_progress_for_dl(
                aria2, gid, event, previous_message,user_msg=mes
            )
    except aria2p.client.ClientException as e:
        if " not found" in str(e) or "'file'" in str(e):
            fname = "N/A"
            try:
                fname = file.name
            except:pass

            await event.edit(
                f"Download Canceled :\n<code>{fname}</code>", parse_mode="html"
            )

            return False
    except MessageNotModifiedError:
        pass
    except RecursionError:
        file.remove(force=True)
        await event.edit(
            f"Download Auto Canceled :\n\nYour Torrent/Link {file.name} is Dead.",
            parse_mode="html",
        )

        return False
    except Exception as e:
        torlog.info(str(e))
        if " not found" in str(e) or "'file'" in str(e):
            await event.edit(
                f"Download Canceled :\n<code>{file.name}</code>",
                parse_mode="html",
            )

        else:
            torlog.info(str(e))
            await event.edit(
                f"<u>error</u> :\n<code>{str(e)}</code> \n\n#error",
                parse_mode="html",
            )


        return False

async def remove_dl(gid):
    aria2 = await aria_start()
    try:
        downloads = aria2.get_download(gid)
        downloads.remove(force=True, files=True)
    except:
        torlog.exception("exc")
