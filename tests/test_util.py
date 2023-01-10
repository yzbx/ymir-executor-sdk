import math
import os
import random
import unittest

import yaml
from easydict import EasyDict as edict
from ymir_exc import result_writer, settings
from ymir_exc.util import (YmirStage, YmirStageWeight, get_bool, get_ymir_process, write_ymir_training_result)


def test_get_ymir_process():
    weights = YmirStageWeight()
    w0, w1, _ = weights.weights
    assert math.isclose(sum(weights.weights), 1)
    for stage, stage_init, stage_weight in zip(
        [YmirStage.PREPROCESS, YmirStage.TASK, YmirStage.POSTPROCESS],
        [0, w0, w0 + w1],
            weights.weights,
    ):
        for _ in range(5):
            p = random.random()
            x = get_ymir_process(stage, p=p)
            assert math.isclose(x, stage_init + p * stage_weight)
            assert 0 <= x <= 1

    for stage, stage_init, stage_weight in zip(
        [YmirStage.PREPROCESS, YmirStage.TASK, YmirStage.POSTPROCESS],
        [0, w0, w0 + w1],
            weights.weights,
    ):
        for _ in range(5):
            p = random.random()
            x = get_ymir_process(stage, p=p, task_idx=0, task_num=2)
            assert math.isclose(x, 0.5 * (stage_init + p * stage_weight))
            assert 0 <= x <= 0.5

            x = get_ymir_process(stage, p=p, task_idx=1, task_num=2)
            assert math.isclose(x, 0.5 + 0.5 * (stage_init + p * stage_weight))
            assert 0.5 <= x <= 1


def test_get_bool():
    cfg = edict()
    cfg.param = edict()
    cfg.param.a = 0
    cfg.param.b = 1
    cfg.param.false = "false"
    cfg.param.true = "true"
    cfg.param.c = False
    cfg.param.d = True
    cfg.param.f = "F"
    cfg.param.t = "T"
    cfg.param.h = "False"
    cfg.param.i = "True"
    for key in ["a", "false", "c", "f", "h"]:
        assert not get_bool(cfg, key)

    for key in ["b", "true", "d", "t", "i"]:
        assert get_bool(cfg, key)

    assert get_bool(cfg, "undefine", True)
    assert not get_bool(cfg, "undefine", False)


class TestWriteResult(unittest.TestCase):

    def __init__(self, methodName: str = ...) -> None:  # type: ignore
        super().__init__(methodName)
        self._test_root = os.path.join("/tmp", "test_tmi", *self.id().split(".")[-3:])
        self._custom_env_file = os.path.join(self._test_root, "env.yml")
        self._training_result_file = os.path.join(self._test_root, 'result.yaml')
        settings.DEFAULT_ENV_FILE_PATH = self._custom_env_file

        env_obj = {
            "task_id": "task0",
            "run_training": True,
            "run_mining": False,
            "run_infer": False,
            "protocol_version": "1.0.0",
            "input": {
                "root_dir": "/in1",
                "assets_dir": "/in1/assets",
                "annotations_dir": "/in1/annotations",
                "models_dir": "/in1/models",
                "training_index_file": '/in1/training-index.tsv',
                "config_file": '/in1/config.yaml',
            },
            "output": {
                "root_dir": "/tmp/out",
                "models_dir": "/tmp/out/models",
                "tensorboard_dir": "/out1/tensorboard",
                "training_result_file": self._training_result_file,
                "mining_result_file": "/out1/result.txt",
                "infer_result_file": "/out1/infer-result.json",
                "monitor_file": "/out1/monitor.txt",
            },
        }

        os.makedirs(os.path.dirname(self._custom_env_file), exist_ok=True)
        with open(self._custom_env_file, "w") as f:
            yaml.safe_dump(env_obj, f)

    def test_write_ymir_traing_result(self):

        def check_training_result(cfg):
            with open(cfg.ymir.output.training_result_file, "r") as f:
                training_result: dict = yaml.safe_load(stream=f)

            if result_writer.multiple_model_stages_supportable():
                assert "model_stages" in training_result.keys()
            else:
                assert "model" in training_result.keys()
                assert "map" in training_result.keys()

        cfg = edict()
        cfg.param = edict()
        cfg.ymir = edict()
        cfg.ymir.output = edict()
        cfg.ymir.output.root_dir = "/tmp/out"
        cfg.ymir.output.models_dir = "/tmp/out/models"
        cfg.ymir.output.training_result_file = self._training_result_file

        os.makedirs(cfg.ymir.output.models_dir, exist_ok=True)

        for i in range(3):
            files = [f"checkpoint_{i}.pth", "config_{i}.json"]
            map50 = random.random()
            id = f"epoch_{i}"

            for f in files:
                with open(os.path.join(cfg.ymir.output.models_dir, f), 'w') as fw:
                    fw.write(f'{f}\n')
            write_ymir_training_result(cfg, evaluation_result=dict(mAP=map50), files=files, id=id)
            check_training_result(cfg)

        write_ymir_training_result(cfg, evaluation_result=dict(mAP=0), id="last", files=[])
        check_training_result(cfg)
