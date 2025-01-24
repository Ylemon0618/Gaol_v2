from modules.make_embed import makeEmbed, Color


class Song:
    def __init__(self):
        pass

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

        timeout = makeEmbed(error_title, "시간초과\n\n다시 시도하여 주세요.", Color.error)

    class Success:
        leave = makeEmbed(":mute: Leave :mute:", "음성 채팅방을 떠납니다.", Color.success)
        pause = makeEmbed(":no_entry: Paused :no_entry:", "재생 중인 노래를 일시정지 했습니다.", Color.success)
        resume = makeEmbed(":musical_note: Resumed :musical_note:", "일시정지 된 노래를 다시 재생했습니다.", Color.success)
        skip = makeEmbed(":musical_note: Skipped :musical_note:", "노래를 스킵했습니다.", Color.success)
        stop = makeEmbed(":musical_note: Stopped :musical_note:", "노래 재생을 중지했습니다.", Color.success)

    class UI:
        convert = makeEmbed(":arrows_counterclockwise: Convert :arrows_counterclockwise:",
                            "변환 할 확장자를 선택 해 주세요.",
                            Color.success)
