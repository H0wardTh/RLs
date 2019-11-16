import gym
import numpy as np
import threading


class FakeMultiThread(threading.Thread):

    def __init__(self, func, args=()):
        super().__init__()
        self.func = func
        self.args = args

    def run(self):
        self.result = self.func(*self.args)

    def get_result(self):
        try:
            return self.result
        except Exception:
            return None


class gym_envs(object):

    def __init__(self, gym_env_name, n, render_mode='first'):
        self.n = n  # environments number
        self.envs = [gym.make(gym_env_name) for _ in range(self.n)]
        self.observation_space = self.envs[0].observation_space
        self.obs_high = self.envs[0].observation_space.high
        self.obs_low = self.envs[0].observation_space.low
        self.obs_type = 'visual' if len(self.observation_space.shape) == 3 else 'vector'
        self.reward_threshold = self.envs[0].env.spec.reward_threshold  # reward threshold refer to solved
        if type(self.envs[0].action_space) == gym.spaces.box.Box:
            self.a_type = 'continuous'
        elif type(self.envs[0].action_space) == gym.spaces.tuple.Tuple:
            self.a_type = 'Tuple(Discrete)'
        else:
            self.a_type = 'discrete'
        self.action_space = self.envs[0].action_space
        self._get_render_index(render_mode)

    def _get_render_index(self, render_mode):
        if isinstance(render_mode, list):
            assert all([isinstance(i, int) for i in render_mode]), 'items in render list must have type of int'
            assert min(index) >= 0, 'index must larger than zero'
            assert max(index) <= self.n, 'render index cannot larger than environment number.'
            self.render_index = render_mode
        elif isinstance(render_mode, str):
            if render_mode == 'first':
                self.render_index = [0]
            elif render_mode == 'last':
                self.render_index = [-1]
            elif render_mode == 'all':
                self.render_index = [i for i in range(self.n)]
            else:
                a, b = render_mode.split('_')
                if a == 'random' and 0 < int(b) <= self.n:
                    import random
                    self.render_index = random.sample([i for i in range(self.n)], int(b))
        else:
            raise Exception('render_mode must be first, last, all, [list] or random_[num]')

    def render(self):
        '''
        render game windows.
        '''
        [self.envs[i].render() for i in self.render_index]

    def close(self):
        '''
        close all environments.
        '''
        [env.close() for env in self.envs]

    def sample_action(self):
        '''
        generate ramdom actions for all training environment.
        '''
        return np.array([env.action_space.sample() for env in self.envs])

    def reset(self):
        self.dones_index = []
        threadpool = []
        for i in range(self.n):
            th = FakeMultiThread(self.envs[i].reset, args=())
            threadpool.append(th)
        for th in threadpool:
            th.start()
        for th in threadpool:
            threading.Thread.join(th)
        return np.array([threadpool[i].get_result() for i in range(self.n)]).astype(np.float32)

        # if self.obs_type == 'visual':
        #     return np.array([threadpool[i].get_result()[np.newaxis, :] for i in range(self.n)]).astype(np.float32)
        # else:
        #     return np.array([threadpool[i].get_result() for i in range(self.n)]).astype(np.float32)

    def step(self, actions):
        if self.a_type == 'discrete':
            actions = actions.reshape(-1,)
        elif self.a_type == 'Tuple(Discrete)':
            actions = actions.reshape(self.n, -1).tolist()
        threadpool = []
        for i in range(self.n):
            th = FakeMultiThread(self.envs[i].step, args=(actions[i], ))
            threadpool.append(th)
        for th in threadpool:
            th.start()
        for th in threadpool:
            threading.Thread.join(th)
        results = [threadpool[i].get_result() for i in range(self.n)]

        # if self.obs_type == 'visual':
        #     results = [
        #         [threadpool[i].get_result()[0][np.newaxis, :], *threadpool[i].get_result()[1:]]
        #         for i in range(self.n)]
        # else:
        #     results = [threadpool[i].get_result() for i in range(self.n)]
        obs, reward, done, info = [np.array(e) for e in zip(*results)]
        self.dones_index = np.where(done)[0]
        return obs.astype(np.float32), reward.astype(np.float32), done, info

    def patial_reset(self):
        threadpool = []
        for i in self.dones_index:
            th = FakeMultiThread(self.envs[i].reset, args=())
            threadpool.append(th)
        for th in threadpool:
            th.start()
        for th in threadpool:
            threading.Thread.join(th)
        return np.array([threadpool[i].get_result() for i in range(self.dones_index.shape[0])]).astype(np.float32)

        # if self.obs_type == 'visual':
        #     return np.array([threadpool[i].get_result()[np.newaxis, :] for i in range(self.dones_index.shape[0])]).astype(np.float32)
        # else:
        #     return np.array([threadpool[i].get_result() for i in range(self.dones_index.shape[0])]).astype(np.float32)
