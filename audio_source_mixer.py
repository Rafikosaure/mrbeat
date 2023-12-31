from array import array

from audiostream.sources.thread import ThreadSource

from audio_source_track import AudioSourceTrack

MAX_16BITS = 32767
MIN_16BITS = -32768


def sum_16bits(n):
    s = sum(n)
    if s > MAX_16BITS:
        s = MAX_16BITS
    if s < MIN_16BITS:
        s = MIN_16BITS
    return s


class AudioSourceMixer(ThreadSource):
    buf = None

    # Mixer -> starter
    #  get_bytes (appelé par la carte son)
    #   -> AudioSourceTrack (on les start pas)
    #       get_bytes (appelé à la main)
    #   -> AudioSourceTrack (on les start pas)
    #       get_bytes (appelé à la main)
    #   -> AudioSourceTrack (on les start pas)
    #       get_bytes (appelé à la main)
    #   -> AudioSourceTrack (on les start pas)
    #       get_bytes (appelé à la main)

    def __init__(self, output_stream, all_wav_samples, bpm, sample_rate, nb_steps, on_current_step_changed, min_bpm, *args, **kwargs):
        ThreadSource.__init__(self, output_stream, *args, **kwargs)

        self.tracks = []
        for i in range(0, len(all_wav_samples)):
            track = AudioSourceTrack(output_stream, all_wav_samples[i], bpm, sample_rate, min_bpm)
            track.set_steps((0,) * nb_steps)
            self.tracks.append(track)

        self.bpm = bpm
        self.buf = None
        self.silence = array("h", b"\x00\x00" * self.tracks[0].buffer_nb_samples)
        self.nb_steps = nb_steps
        self.min_bpm = min_bpm
        self.current_sample_index = 0
        self.current_step_index = 0
        self.sample_rate = sample_rate
        self.on_current_step_changed = on_current_step_changed
        self.is_playing = False

    # Notre sample_rate = 44100
    # Notre step_nb_samples, c'est le nombre de samples dont on a besoin pour 1 pas (step)
    # 1 pas = 44100 * 15 / BPM
    # ou autrement dit : step_nb_samples = sample_rate * 15 / BPM

    def set_steps(self, index, steps):
        if index >= len(self.tracks):
            return
        if not len(steps) == self.nb_steps:
            self.tracks[index].set_steps(steps)

    def set_bpm(self, bpm):
        if bpm < self.min_bpm:
            return
        self.bpm = bpm

    def audio_play(self):
        self.is_playing = True

    def audio_stop(self):
        self.is_playing = False

    def get_bytes(self, *args, **kwargs):

        for i in range(0, len(self.tracks)):
            self.tracks[i].set_bpm(self.bpm)

        step_nb_samples = self.tracks[0].step_nb_samples

        # silence
        if not self.is_playing:
            return self.silence[0:step_nb_samples].tobytes()

        track_buffers = []
        for i in range(0, len(self.tracks)):
            track = self.tracks[i]
            track_buffer = track.get_bytes_array()
            track_buffers.append(track_buffer)

        # for i in range(0, step_nb_samples):
        #     self.buf[i] = 0
        #     for j in range(0, len(track_buffers)):
        #         self.buf[i] += track_buffers[j][i]

        s = map(sum_16bits, zip(*track_buffers))
        self.buf = array("h", s)

        if self.on_current_step_changed is not None:
            # Décalage de 2 steps pour synchroniser l'affichage du step courant
            # et du son entendu (à cause des buffers audio)
            step_index_for_display = self.current_step_index - 2
            if step_index_for_display < 0:
                step_index_for_display += self.nb_steps
            self.on_current_step_changed(step_index_for_display)

        self.current_step_index += 1
        if self.current_step_index >= self.nb_steps:
            self.current_step_index = 0

        return self.buf[0:step_nb_samples].tobytes()

