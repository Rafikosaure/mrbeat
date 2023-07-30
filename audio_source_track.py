from array import array

from audiostream.sources.thread import ThreadSource


class AudioSourceTrack(ThreadSource):
    steps = ()
    step_nb_samples = 0

    def __init__(self, output_stream, wav_samples, bpm, sample_rate, min_bpm, *args, **kwargs):
        ThreadSource.__init__(self, output_stream, *args, **kwargs)
        self.current_sample_index = 0
        self.current_step_index = 0
        self.wav_samples = wav_samples
        self.nb_wav_samples = len(wav_samples)
        self.min_bpm = min_bpm
        self.bpm = bpm
        self.sample_rate = sample_rate
        self.last_sound_sample_start_index = -self.nb_wav_samples
        self.step_nb_samples = self.compute_step_nb_samples(bpm)
        self.buffer_nb_samples = self.compute_step_nb_samples(min_bpm)
        self.silence = array("h", b"\x00\x00" * self.buffer_nb_samples)

        if not self.bpm == 0:
            n = int(self.sample_rate*15/self.bpm)
            if not n == self.step_nb_samples:
                self.step_nb_samples = n

    # Notre sample_rate = 44100
    # Notre step_nb_samples, c'est le nombre de samples dont on a besoin pour 1 pas (step)
    # 1 pas = 44100 * 15 / BPM
    # ou autrement dit : step_nb_samples = sample_rate * 15 / BPM

    def set_steps(self, steps):
        if not len(steps) == len(self.steps):
            self.current_step_index = 0
        self.steps = steps

    def set_bpm(self, bpm):
        self.bpm = bpm
        self.step_nb_samples = self.compute_step_nb_samples(bpm)

    def compute_step_nb_samples(self, bpm_value):
        if not bpm_value == 0:
            n = int(self.sample_rate * 15 / bpm_value)
            return n
        return 0

    def no_steps_activated(self):
        if len(self.steps) == 0:
            return True
        for i in range(len(self.steps)):
            if self.steps[i] == 1:
                return False
        return True

    def get_bytes_array(self):
        result_buf = None

        # 1 - Aucun pas d'activé -> silence
        if self.no_steps_activated():
            result_buf = self.silence[0:self.step_nb_samples]
        elif self.steps[self.current_step_index] == 1:
            # 2 - Step activé et le son a plus de samples que 1 step
            self.last_sound_sample_start_index = self.current_sample_index
            if self.nb_wav_samples >= self.step_nb_samples:
                result_buf = self.wav_samples[0:self.step_nb_samples]
            else:
                # 3 - Step activé et le son a moins de samples que 1 step
                silence_nb_samples = self.step_nb_samples - self.nb_wav_samples
                result_buf = self.wav_samples[0:self.nb_wav_samples]
                result_buf.extend(self.silence[0:silence_nb_samples])
        else:
            # 4 - Le step n'est pas activé mais on doit jouer la suite du son
            index = self.current_sample_index - self.last_sound_sample_start_index
            # 4.1 - Ce qu'il nous reste à jouer est plus long qu'un step
            if index > self.nb_wav_samples:
                # 5 - Le step n'est pas activé et on a fini de jouer le son -> silence
                result_buf = self.silence[0:self.step_nb_samples]
            elif self.nb_wav_samples - index >= self.step_nb_samples:
                result_buf = self.wav_samples[index:self.step_nb_samples+index]
            else:
                # 4.2 - Ce qu'il nous reste à jouer est plus petit qu'un step
                silence_nb_samples = self.step_nb_samples - self.nb_wav_samples + index
                result_buf = self.wav_samples[index:self.nb_wav_samples]
                result_buf.extend(self.silence[0:silence_nb_samples])

        self.current_sample_index += self.step_nb_samples

        self.current_step_index += 1
        if self.current_step_index >= len(self.steps):
            self.current_step_index = 0

        if result_buf is None:
            print("result_buf is None")
        elif not len(result_buf) == self.step_nb_samples:
            print("result_buf len is not step_nb_samples")

        return result_buf

    def get_bytes(self, *args, **kwargs):
        return self.get_bytes_array().tobytes()

