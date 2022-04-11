import os
import sys
import time
from os import makedirs
from os.path import join, exists

import numpy as np
import ptan
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from ptan.agent import default_states_preprocessor
from torch.utils.tensorboard import SummaryWriter

from fedot.core.utils import fedot_project_root, default_fedot_data_dir
from fedot.rl.pipeline_env import PipelineEnv

GAMMA = 0.99

LEARNING_RATE = 0.001
ENTROPY_BETA = 0.35
BATCH_SIZE = 128
NUM_ENVS = 50

REWARD_STEPS = 5
CLIP_GRAD = 0.1


class A2CRnn(nn.Module):
    def __init__(self, state_dim, action_dim, hidden_dim=128):
        super(A2CRnn, self).__init__()

        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim)
        )

        """ Возвращает политику (стратегию) с распределением вероятности по действиям """
        self.policy = nn.Sequential(
            nn.Linear(hidden_dim, 512),
            nn.ReLU(),
            nn.Linear(512, action_dim)
        )

        """ Число, которое приблизительно соответствует ценности состояния """
        self.value = nn.Sequential(
            nn.Linear(hidden_dim, 512),
            nn.ReLU(),
            nn.Linear(512, 1)
        )

    def forward(self, state):
        x = self.net(state.float())

        return self.policy(x), self.value(x)


class RewardTracker:
    def __init__(self, writer, stop_reward):
        self.writer = writer
        self.stop_reward = stop_reward
        self.ts_frame = None
        self.ts = None

    def __enter__(self):
        self.ts = time.time()
        self.ts_frame = 0
        self.total_rewards = []
        return self

    def __exit__(self, *args):
        self.writer.close()

    def reward(self, reward, episode, epsilon=None):
        self.total_rewards.append(reward)
        mean_reward = np.mean(self.total_rewards[-100:])
        epsilon_str = "" if epsilon is None else ", eps %.2f" % epsilon
        print("%d: done %d episode, mean reward %.3f, %s" % (
            episode, len(self.total_rewards), mean_reward, epsilon_str
        ))
        sys.stdout.flush()

        if epsilon is not None:
            self.writer.add_scalar("epsilon", epsilon, episode)

        self.writer.add_scalar("reward_100", mean_reward, episode)
        self.writer.add_scalar("reward", reward, episode)

        if mean_reward > self.stop_reward:
            print("Solved in %d frames!" % episode)
            return True

        return False


def unpack_batch(batch, net, device):
    """
    Convert batch into training tensors
    :param batch:
    :param net:
    :return: states variable, actions tensor, reference values variable
    """
    states = []
    actions = []
    rewards = []
    not_done_idx = []
    last_states = []

    # Проходим по обучающему набору переходов и копируем их поля в списки
    for idx, exp in enumerate(batch):
        states.append(np.array(exp.state, copy=False))
        actions.append(int(exp.action))
        rewards.append(exp.reward)  # Дисконтированная награда
        if exp.last_state is not None:
            not_done_idx.append(idx)
            last_states.append(np.array(exp.last_state, copy=False))

    # Заводим переменные для вычисления на Torch
    states_v = torch.FloatTensor(np.array(states, copy=False)).to(device)
    actions_t = torch.LongTensor(actions).to(device)

    # handle rewards
    rewards_np = np.array(rewards, dtype=np.float32)
    if not_done_idx:
        # Подготавливаем переменную с последним состоянием в цепочке переходов
        last_states_v = torch.FloatTensor(np.array(last_states, copy=False)).to(device)
        # Запрашиваем аппроксимацию V(s)
        last_vals_v = net(last_states_v)[1]
        last_vals_np = last_vals_v.data.cpu().numpy()[:, 0]
        # Добавляем значение к дисконтированному вознаграждению
        rewards_np[not_done_idx] += GAMMA ** REWARD_STEPS * last_vals_np

    ref_vals_v = torch.FloatTensor(rewards_np).to(device)
    return states_v, actions_t, ref_vals_v


if __name__ == '__main__':
    file_path_train = 'cases/data/scoring/scoring_train.csv'
    full_path_train = os.path.join(str(fedot_project_root()), file_path_train)

    file_path_valid = 'cases/data/scoring/scoring_test.csv'
    full_path_valid = os.path.join(str(fedot_project_root()), file_path_valid)

    make_env = lambda: PipelineEnv(full_path_train)
    envs = [make_env() for _ in range(NUM_ENVS)]
    in_dim = envs[0].observation_space.shape[0]
    out_dim = envs[0].action_space.n

    test_env = PipelineEnv(path_to_data=full_path_train, path_to_valid=full_path_valid)

    device = torch.device('cuda' if torch.cuda.is_available() else "cpu")

    pnet = A2CRnn(in_dim, out_dim).to(device)
    print(pnet)

    agent = ptan.agent.PolicyAgent(lambda x: pnet(x)[0], apply_softmax=True, device=device)
    exp_source = ptan.experience.ExperienceSourceFirstLast(envs, agent, gamma=GAMMA, steps_count=REWARD_STEPS)

    optimizer = optim.Adam(pnet.parameters(), lr=LEARNING_RATE, eps=1e-3)

    # Tensorboard
    path_to_tbX = join(default_fedot_data_dir(), 'rl', 'tensorboard')
    if not exists(path_to_tbX):
        makedirs(path_to_tbX)

    # Save model
    path_to_checkpoint = join(default_fedot_data_dir(), 'rl', 'checkpoint')
    if not exists(path_to_checkpoint):
        makedirs(path_to_checkpoint)

    tb_writer = SummaryWriter(log_dir=path_to_tbX)

    total_rewards = []
    step_idx = 0
    done_episodes = 0
    reward_sum = 0.0

    best_mean_rewards = 0

    batch = []

    with RewardTracker(tb_writer, stop_reward=75) as tracker:
        with ptan.common.utils.TBMeanTracker(tb_writer, batch_size=10) as tb_tracker:
            for step_idx, exp in enumerate(exp_source):
                batch.append(exp)

                new_rewards = exp_source.pop_total_rewards()

                if new_rewards:
                    if tracker.reward(new_rewards[0], step_idx):
                        break

                if (step_idx % 500) == 0 and step_idx != 0:
                    path_to_save = join(path_to_checkpoint, f'agent_{step_idx}')
                    torch.save(pnet.state_dict(), path_to_save)

                    with torch.no_grad():
                        total_rewards = []

                        for episode in range(25):
                            state = test_env.reset()
                            done = False

                            while not done:
                                state = default_states_preprocessor(state).to(device)
                                logits_v, _ = pnet(state)

                                prob_v = F.softmax(logits_v)
                                prob = prob_v.data.cpu().numpy()
                                action = np.random.choice(len(prob), p=prob)
                                state, reward, done, info = test_env.step(action, mode='test')
                                total_rewards.append(reward)

                    tb_writer.add_scalar("valid_reward", np.mean(total_rewards), step_idx)

                if len(batch) < BATCH_SIZE:
                    continue

                # Процесс подсчета loss

                states_v, actions_t, vals_ref_v = unpack_batch(batch, pnet, device=device)
                batch.clear()

                optimizer.zero_grad()

                logits_v, value_v = pnet(states_v)
                # Рассчитываем MSE между значением, возвращенным сетью, и аппроксимацией, выполненной
                # с помощью уравнения Беллмана, развернутного на REWARD_STEPS вперед
                loss_value_v = F.mse_loss(value_v.squeeze(-1), vals_ref_v)

                # Рассчитываем потери, связанные со стратегией, чтобы выполнить градиенты по стратегиям.
                # Два первых шага заключаются в вычислении логарифма вероятности действий по формуле:
                # A(s, a) = Q(s, a) - V(s)
                log_prob_v = F.log_softmax(logits_v, dim=1)
                adv_v = vals_ref_v - value_v.squeeze(-1).detach()
                # Вычисляем логарифм вероятностей для выбранных действий
                # и масштабируем их с помощью adv_v.
                log_prob_actions_v = adv_v * log_prob_v[range(BATCH_SIZE), actions_t]
                # Значение потерь при PG будет равно взятому с обратным знаком среднему для данных
                # масштабированных логарифмов вероятностей
                loss_policy_v = -log_prob_actions_v.mean()

                # Рассчитываем потери на энтропию
                prob_v = F.softmax(logits_v, dim=1)
                entropy_loss_v = ENTROPY_BETA * (prob_v * log_prob_v).sum(dim=1).mean()

                # Просчитываем градиенты
                loss_policy_v.backward(retain_graph=True)
                grads = np.concatenate([p.grad.data.cpu().numpy().flatten()
                                        for p in pnet.parameters()
                                        if p.grad is not None])

                loss_v = entropy_loss_v + loss_value_v
                loss_v.backward()
                nn.utils.clip_grad_norm_(pnet.parameters(), CLIP_GRAD)
                optimizer.step()

                loss_v += loss_policy_v

                tb_tracker.track("advantage", adv_v, step_idx)
                tb_tracker.track("values", value_v, step_idx)
                tb_tracker.track("batch_rewards", vals_ref_v, step_idx)
                tb_tracker.track("loss_entropy", entropy_loss_v, step_idx)
                tb_tracker.track("loss_policy", loss_policy_v, step_idx)
                tb_tracker.track("loss_value", loss_value_v, step_idx)
                tb_tracker.track("loss_total", loss_v, step_idx)
                tb_tracker.track("grad_l2", np.sqrt(np.mean(np.square(grads))), step_idx)
                tb_tracker.track("grad_max", np.max(np.abs(grads)), step_idx)
                tb_tracker.track("grad_var", np.var(grads), step_idx)
