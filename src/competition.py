import random
from collections import namedtuple

from .competitor import Competitor

from pommerman.cli import run_battle

Args = namedtuple("Args", [
    "config",
    "agents",
    "agent_env_vars",
    "record_pngs_dir",
    "record_json_dir",
    "render",
    "render_mode",
    "game_state_file",
    "do_sleep",
])

simple_agent = "test::agents.SimpleAgent"
default_args = Args(config="PommeFFACompetition-v0",
                    agents=",".join([simple_agent] * 4),
                    agent_env_vars="",
                    record_pngs_dir=None,
                    record_json_dir=None,
                    render=False,
                    render_mode="human",
                    game_state_file=None,
                    do_sleep=True)

class Competition:
    def __init__(self, competitor_1: Competitor, competitor_2: Competitor):
        self.competitor_1 = competitor_1
        self.competitor_2 = competitor_2

    def run(self):
        info = run_battle.run(default_args, num_times=1)[0]
        return info
