import os
os.environ['KMP_DUPLICATE_LIB_OK']='True'

import random, datetime
from pathlib import Path

import gym
import gym_super_mario_bros
from gym.wrappers import FrameStack, GrayScaleObservation, TransformObservation
from nes_py.wrappers import JoypadSpace

from gym.spaces import Box

from metrics import MetricLogger
from agent import Mario
from wrappers import ResizeObservation, SkipFrame

import gc
import torch

startTime = datetime.datetime.now()

# Initialize Super Mario environment
env = gym_super_mario_bros.make('SuperMarioBros-v3', apply_api_compatibility=True)

# Limit the action-space to
#   0. walk right
#   1. jump right
env = JoypadSpace(
    env,
    [['right'],
    ['right', 'A']]
)

# Apply Wrappers to environment
env = SkipFrame(env, skip=4)
env = GrayScaleObservation(env, keep_dim=False)
env = ResizeObservation(env, shape=84)
env = TransformObservation(env, f=lambda x: x / 255.)
env = FrameStack(env, num_stack=4)

env.reset()

save_dir = Path('checkpoints') / datetime.datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
save_dir.mkdir(parents=True)

checkpoint = None
mario = Mario(state_dim=(4, 84, 84), action_dim=env.action_space.n, save_dir=save_dir, checkpoint=checkpoint)

logger = MetricLogger(save_dir)

episodes = 40000
#episodes = 100

### for Loop that train the model num_episodes times by playing the game
for e in range(episodes):

    state, info = env.reset()

    # Play the game!
    while True:

        # 3. Show environment (the visual) [WIP]
        env.render()

        # 4. Run agent on the state
        action = mario.act(state)

        # 5. Agent performs action
        next_state, reward, truncated, terminated, info = env.step(action)
        done = truncated or terminated

        # 6. Remember
        mario.cache(state, next_state, action, reward, done)

        # 7. Learn
        q, loss = mario.learn()

        # 8. Logging
        logger.log_step(reward, loss, q)

        # 9. Update state
        state = next_state

        # 10. Check if end of game
        if done or info['flag_get']:
            break

    logger.log_episode()

    #print("Episode done: {} - Steps: {}".format(e,mario.curr_step))

    if e % 50 == 0:
        logger.record(
            episode=e,
            epsilon=mario.exploration_rate,
            step=mario.curr_step
        )

# save the final model
mario.save()

delta = datetime.datetime.now() - startTime
print("Elapsed time = {}".format(delta))