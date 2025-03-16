from modules.make_embed import makeEmbed, Color


class SongEmbed:
    class Error:
        error_title = ":warning: Error :warning:"

        empty_queue = makeEmbed(error_title, "현재 대기열이 비어있습니다.", Color.error)

        invalid_file = makeEmbed(error_title, "유효하지 않은 파일입니다.", Color.error)
        invalid_option = makeEmbed(error_title, "유효하지 않은 옵션입니다.", Color.error)
        invalid_url = makeEmbed(error_title, "유효하지 않은 URL입니다.", Color.error)
        invalid_value = makeEmbed(error_title, "유효하지 않은 값입니다.", Color.error)
        invalid_voice = makeEmbed(error_title, "유효하지 않은 음성 채팅방입니다.", Color.error)

        not_connected = makeEmbed(error_title, "음성 채팅방에 접속해야 합니다.", Color.error)
        not_found = makeEmbed(error_title, "노래를 찾을 수 없습니다.", Color.error)
        not_paused = makeEmbed(error_title, "현재 재생이 중지된 노래가 없습니다.", Color.error)
        not_playing = makeEmbed(error_title, "노래가 재생중이어야 합니다.", Color.error)
        not_repeating = makeEmbed(error_title, "대기열을 반복하고 있지 않습니다.", Color.error)

        timeout = makeEmbed(error_title, "시간초과\n\n다시 시도하여 주세요.", Color.error)

    class Success:
        leave = makeEmbed(":mute: Leave :mute:", "음성 채팅방을 떠납니다.", Color.success)
        pause = makeEmbed(":no_entry: Paused :no_entry:", "재생 중인 노래를 일시정지 했습니다.", Color.success)
        resume = makeEmbed(":musical_note: Resumed :musical_note:", "일시정지 된 노래를 다시 재생했습니다.", Color.success)
        skip = makeEmbed(":musical_note: Skipped :musical_note:", "노래를 스킵했습니다.", Color.success)
        stop = makeEmbed(":musical_note: Stopped :musical_note:", "노래 재생을 중지했습니다.", Color.success)
        repeat = makeEmbed(":arrows_counterclockwise: Repeat :arrows_counterclockwise:", f"대기열을 반복합니다.", Color.success)
        stop_repeat = makeEmbed(":arrows_counterclockwise: Repeat :arrows_counterclockwise:", f"대기열 반복을 중지했습니다.",
                                Color.success)

    class UI:
        convert = makeEmbed(":arrows_counterclockwise: Convert :arrows_counterclockwise:",
                            "변환 할 확장자를 선택 해 주세요.",
                            Color.success)

        repeat_confirm = makeEmbed("Confirm", f"이미 대기열을 반복중입니다.", Color.warning)


class HelpEmbed:
    choose_item = makeEmbed(":speech_left: Help :speech_left:",
                            "Do you need some help?\nPlease select an item below.\n\n도움이 필요하신가요?\n아래에서 항목을 선택 해 주세요.",
                            Color.success)

    choose_command = makeEmbed(":question: Command List | 명령어 도움말 :question:",
                               "Please choose a group of commands you need help with.\n\n사용법이 궁금한 명령어를 아래에서 선택 해 주세요.",
                               Color.success)

    commands = {
        "song": {
            "ko": makeEmbed(":musical_note: Song | 노래 :musical_note:",
                            "음악 재생과 관련된 명령어입니다.\n[yt-dlp](<https://github.com/yt-dlp/yt-dlp>) 라이브러리를 사용해 제작되었습니다.\n\n*이 명령어는 유튜브의 정책을 지키지 않을 수도 있습니다.*\nㅤ\nㅤ",
                            Color.success),
            "en": makeEmbed(":musical_note: Song | 노래 :musical_note:",
                            "Commands for playing music.\nThese commands are created using a library: [yt-dlp](<https://github.com/yt-dlp/yt-dlp>).\n\n*These commands may not comply with YouTube's policy.*\nㅤ\nㅤ",
                            Color.success)
        },
        "file": {
            "ko": makeEmbed(":file_folder: File | 파일 :file_folder:",
                            "파일 관리를 위한 명령어입니다.\nㅤ\nㅤ",
                            Color.success),
            "en": makeEmbed(":file_folder: File | 파일 :file_folder:",
                            "Commands for managing files.\nㅤ\nㅤ",
                            Color.success)
        },
        "music": {
            "ko": makeEmbed(":musical_keyboard: Music | 음악 :musical_keyboard:",
                            "음악과 관련된 명령어입니다.\n\n*이 명령어는 노래를 재생하는 명령어가 아닙니다.\n음악 재생은* `/노래` *를 이용해 주세요.*\nㅤ\nㅤ",  # 줄 구분용 공백문자
                            Color.success),
            "en": makeEmbed(":musical_keyboard: Music | 음악 :musical_keyboard:",
                            "Commands for music.\n\n*These commands do not play songs.\nTo play music, please use* `/Song` *instead.*\nㅤ\nㅤ",  # 줄 구분용 공백문자
                            Color.success)
        },
        "game": {
            "ko": makeEmbed(":video_game: Game | 게임 :video_game:",
                            "봇 또는 유저와 게임을 플레이 할 수 있는 명령어입니다.\nㅤ\nㅤ",
                            Color.success),
            "en": makeEmbed(":video_game: Game | 게임 :video_game:",
                            "Commands for playing game with the bot or user.\nㅤ\nㅤ",
                            Color.success)
        },
        "utils": {
            "ko": makeEmbed(":grey_question: Utils | 유틸리티 :grey_question:",
                            "각종 기능들을 사용할 수 있는 명령어입니다.\nㅤ\nㅤ",
                            Color.success),
            "en": makeEmbed(":grey_question: Utils | 유틸리티 :grey_question:",
                            "Commands of utility.\nㅤ\nㅤ",
                            Color.success)
        }
    }
