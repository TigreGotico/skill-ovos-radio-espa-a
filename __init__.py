from os.path import join, dirname
from typing import Iterable

from json_database import JsonStorage
from ovos_utils import classproperty
from ovos_utils.parse import fuzzy_match, MatchStrategy
from ovos_utils.process_utils import RuntimeRequirements
from ovos_workshop.backwards_compat import MediaType, PlaybackType, MediaEntry, Playlist
from ovos_workshop.decorators.ocp import ocp_search, ocp_featured_media
from ovos_workshop.skills.common_play import OVOSCommonPlaybackSkill


class RadioEspañaSkill(OVOSCommonPlaybackSkill):

    def __init__(self, *args, **kwargs):
        self.db = JsonStorage(f"{dirname(__file__)}/res/radios_es.json")
        super().__init__(supported_media=[MediaType.MUSIC,
                                          MediaType.RADIO,
                                          MediaType.GENERIC],
                         skill_icon=join(dirname(__file__), "radios_es.png"),
                         skill_voc_filename="radioespaña_skill",
                         *args, **kwargs)

    def initialize(self):
        # register with OCP to help classifier pick MediaType.RADIO
        self.register_ocp_keyword(MediaType.RADIO,
                                  "radio_station", [s["name"] for s in self.db.values()])
        self.register_ocp_keyword(MediaType.RADIO,
                                  "radio_streaming_provider",
                                  ["Radio españa", "Radio Espanhola", "Radio de España"])

    @classproperty
    def runtime_requirements(self):
        return RuntimeRequirements(internet_before_load=True,
                                   network_before_load=True,
                                   gui_before_load=False,
                                   requires_internet=True,
                                   requires_network=True,
                                   requires_gui=False,
                                   no_internet_fallback=False,
                                   no_network_fallback=False,
                                   no_gui_fallback=True)

    @ocp_featured_media()
    def featured_media(self) -> Playlist:
        pl = Playlist(media_type=MediaType.RADIO,
                      title="Radios de España (All stations)",
                      playback=PlaybackType.AUDIO,
                      image="https://radioespaña.com/img3/LoneDJsquare400.jpg",
                      skill_id=self.skill_id,
                      artist="Radios de España",
                      match_confidence=100,
                      skill_icon=self.skill_icon)
        pl += [MediaEntry(media_type=MediaType.RADIO,
                          uri=ch["stream"],
                          title=ch["name"],
                          playback=PlaybackType.AUDIO,
                          image=ch["image"],
                          skill_id=self.skill_id,
                          artist="Radios de España",
                          match_confidence=90,
                          length=-1,  # live stream
                          skill_icon=self.skill_icon)
               for ch in self.db.values() if ch.get("stream")]
        return pl

    @ocp_search()
    def ocp_radio_españa_playlist(self, phrase: str, media_type: MediaType) -> Iterable[Playlist]:
        if self.voc_match(phrase, "radioespaña", exact=media_type != MediaType.RADIO):
            yield self.featured_media()

    @ocp_search()
    def search_radio_españa(self, phrase, media_type) -> Iterable[MediaEntry]:
        base_score = 0

        if media_type == MediaType.RADIO:
            base_score += 20
        else:
            base_score -= 30

        if self.voc_match(phrase, "radio"):
            base_score += 10

        if self.voc_match(phrase, "radioespaña"):
            base_score += 30  # explicit request
            phrase = self.remove_voc(phrase, "radioespaña")

        results = []
        for ch in self.db.values():
            if not ch.get("stream"):
                continue
            score = round(base_score + fuzzy_match(ch["name"].lower(), phrase.lower(),
                                                   strategy=MatchStrategy.DAMERAU_LEVENSHTEIN_SIMILARITY) * 100)
            if score < 60:
                continue
            results.append(MediaEntry(media_type=MediaType.RADIO,
                             uri=ch["stream"],
                             title=ch["name"],
                             playback=PlaybackType.AUDIO,
                             image=ch["image"],
                             skill_id=self.skill_id,
                             artist="Radios de España",
                             match_confidence=min(100, score),
                             length=-1,  # live stream
                             skill_icon=self.skill_icon))
        results.sort(key=lambda k: k.match_confidence, reverse=True)
        return results


if __name__ == "__main__":
    from ovos_utils.messagebus import FakeBus
    from ovos_utils.log import LOG

    LOG.set_level("DEBUG")

    s = RadioEspañaSkill(bus=FakeBus(), skill_id="t.fake")
    for r in s.ocp_radio_españa_playlist("spanish radio", MediaType.RADIO):
        print(r)
        # Playlist(title='Radios de España (All stations)', artist='Radios de España', position=0, image='https://radioespaña.com/img3/LoneDJsquare400.jpg', match_confidence=100, skill_id='t.fake', skill_icon='/home/miro/PycharmProjects/skill-ovos-radio-españa/radios_es.png', playback=<PlaybackType.AUDIO: 2>, media_type=<MediaType.RADIO: 7>)

    for r in s.search_radio_españa("Catalunya", MediaType.RADIO):
        print(r)
        # MediaEntry(uri='https://directes-radio-int.ccma.cat/live-content/catalunya-radio-hls/master.m3u8', title='Catalunya Ràdio', artist='Radios de España', match_confidence=80, skill_id='t.fake', playback=<PlaybackType.AUDIO: 2>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.RADIO: 7>, length=-1, image='https://static.mytuner.mobi/media/radios-150px/U2sZf5fpTc.png', skill_icon='/home/miro/PycharmProjects/skill-ovos-radio-españa/radios_es.png', javascript='')
        # MediaEntry(uri='https://directes-radio-int.ccma.cat/int/mp4:catmusica/playlist.m3u8', title='Catalunya Música', artist='Radios de España', match_confidence=76, skill_id='t.fake', playback=<PlaybackType.AUDIO: 2>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.RADIO: 7>, length=-1, image='https://cdn.mytuner.mobi/static/ctr/images/radio-default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-radio-españa/radios_es.png', javascript='')
        # MediaEntry(uri='https://wecast17-h-cloud.flumotion.com/copesedes/caceres.mp3', title='LOS 40 Catalunya', artist='Radios de España', match_confidence=76, skill_id='t.fake', playback=<PlaybackType.AUDIO: 2>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.RADIO: 7>, length=-1, image='https://cdn.mytuner.mobi/static/ctr/images/radio-default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-radio-españa/radios_es.png', javascript='')
        # MediaEntry(uri='https://shoutcast.ccma.cat/ccma/catalunyainformacio.mp3', title='Catalunya Informació', artist='Radios de España', match_confidence=65, skill_id='t.fake', playback=<PlaybackType.AUDIO: 2>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.RADIO: 7>, length=-1, image='https://cdn.mytuner.mobi/static/ctr/images/radio-default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-radio-españa/radios_es.png', javascript='')
        # MediaEntry(uri='https://25553.live.streamtheworld.com/SER_CAT_SC', title='Cadena SER Catalunya', artist='Radios de España', match_confidence=65, skill_id='t.fake', playback=<PlaybackType.AUDIO: 2>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.RADIO: 7>, length=-1, image='https://static.mytuner.mobi/media/radios-150px/82524pxgweqy.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-radio-españa/radios_es.png', javascript='')
        # MediaEntry(uri='https://www.catmusica.cat/directes/catclassica_http.m3u', title='CatClàssica', artist='Radios de España', match_confidence=65, skill_id='t.fake', playback=<PlaybackType.AUDIO: 2>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.RADIO: 7>, length=-1, image='https://static.mytuner.mobi/media/radios-150px/LHcAxz7a58.png', skill_icon='/home/miro/PycharmProjects/skill-ovos-radio-españa/radios_es.png', javascript='')
        # MediaEntry(uri='http://srv0435.lcinternet.com:9522/stream', title='Radio Unión Catalunya', artist='Radios de España', match_confidence=63, skill_id='t.fake', playback=<PlaybackType.AUDIO: 2>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.RADIO: 7>, length=-1, image='https://cdn.mytuner.mobi/static/ctr/images/radio-default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-radio-españa/radios_es.png', javascript='')
        # MediaEntry(uri='http://srv0435.lcinternet.com:9522/stream', title='Radio Unión Catalunya', artist='Radios de España', match_confidence=63, skill_id='t.fake', playback=<PlaybackType.AUDIO: 2>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.RADIO: 7>, length=-1, image='https://cdn.mytuner.mobi/static/ctr/images/radio-default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-radio-españa/radios_es.png', javascript='')
        # MediaEntry(uri='https://wecast-b03-01.flumotion.com/canalmalaga/live.mp3', title='Canal Málaga', artist='Radios de España', match_confidence=62, skill_id='t.fake', playback=<PlaybackType.AUDIO: 2>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.RADIO: 7>, length=-1, image='https://static.mytuner.mobi/media/radios-150px/uksr3vhttzzx.png', skill_icon='/home/miro/PycharmProjects/skill-ovos-radio-españa/radios_es.png', javascript='')
        # MediaEntry(uri='https://costablancafm.stream:18106/live', title='Costa Blanca FM', artist='Radios de España', match_confidence=60, skill_id='t.fake', playback=<PlaybackType.AUDIO: 2>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.RADIO: 7>, length=-1, image='https://cdn.mytuner.mobi/static/ctr/images/radio-default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-radio-españa/radios_es.png', javascript='')
