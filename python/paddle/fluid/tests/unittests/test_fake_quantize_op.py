#   Copyright (c) 2018 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

import unittest
import numpy as np
from op_test import OpTest
import paddle.fluid.core as core


class TestFakeQuantizeOp(OpTest):
    def setUp(self):
        self.op_type = "fake_quantize_abs_max"
        self.attrs = {'bit_length': 8}
        self.inputs = {'X': np.random.random((124, 240)).astype("float32"), }
        scale = np.max(np.abs(self.inputs['X'])).astype("float32")
        self.outputs = {
            'Out': np.round(self.inputs['X'] / scale * (
                (1 << (self.attrs['bit_length'] - 1)) - 1)),
            'OutScale': np.array(scale).astype("float32"),
        }

    def test_check_output(self):
        self.check_output()


class TestFakeQuantizeOp1(OpTest):
    def setUp(self):
        self.op_type = "fake_quantize_abs_max"
        self.attrs = {'bit_length': 8}
        self.inputs = {'X': np.zeros((10, 10)).astype("float32"), }
        scale = np.max(np.abs(self.inputs['X'])).astype("float32")
        inv_scale = 1.0 / (scale + 1e-6) if scale < 1e-30 else 1.0 / scale
        self.outputs = {
            'Out': np.round(self.inputs['X'] * inv_scale * (
                (1 << (self.attrs['bit_length'] - 1)) - 1)),
            'OutScale': np.array(scale).astype("float32"),
        }

    def test_check_output(self):
        self.check_output()


class TestFakeQuantizeOp2(OpTest):
    def setUp(self):
        self.op_type = "fake_quantize_abs_max"
        self.attrs = {'bit_length': 8}
        self.inputs = {'X': np.full((10, 10), 1e-40).astype("float32"), }
        scale = np.max(np.abs(self.inputs['X'])).astype("float32")
        inv_scale = 1.0 / (scale + 1e-6) if scale < 1e-30 else 1.0 / scale
        self.outputs = {
            'Out': np.round(self.inputs['X'] * inv_scale * (
                (1 << (self.attrs['bit_length'] - 1)) - 1)),
            'OutScale': np.array(scale).astype("float32"),
        }

    def test_check_output(self):
        self.check_output()


class TestFakeChannelWiseQuantizeOp(OpTest):
    def setUp(self):
        self.set_arg()
        assert self.quant_axis in [0, 1], "quant_axis should be 0 or 1."

        self.op_type = "fake_channel_wise_quantize_abs_max"
        self.attrs = {'bit_length': 8, 'quant_axis': self.quant_axis}

        scales = []
        outputs = self.inputs['X'].copy()
        bnt = (1 << (self.attrs['bit_length'] - 1)) - 1
        if self.quant_axis == 0:
            for i in range(self.inputs['X'].shape[0]):
                scale_v = np.max(np.abs(self.inputs['X'][i])).astype("float32")
                scales.append(scale_v)
                outputs[i] = np.round(outputs[i] / scale_v * bnt)
        elif self.quant_axis == 1:
            for i in range(self.inputs['X'].shape[1]):
                scale_v = np.max(np.abs(self.inputs['X'][:, i])).astype(
                    "float32")
                scales.append(scale_v)
                outputs[:, i] = np.round(outputs[:, i] / scale_v * bnt)

        self.outputs = {
            'Out': outputs,
            'OutScale': np.array(scales).astype("float32"),
        }

    def set_arg(self):
        self.quant_axis = 0
        self.inputs = {
            'X': np.random.random((20, 15, 6, 6)).astype("float32"),
        }

    def test_check_output(self):
        self.check_output()


class TestFakeChannelWiseQuantizeOp1(TestFakeChannelWiseQuantizeOp):
    def set_quant_axis(self):
        self.quant_axis = 1
        self.inputs = {
            'X': np.random.random((15, 20, 5, 5)).astype("float32"),
        }


class TestFakeChannelWiseQuantizeOp2(TestFakeChannelWiseQuantizeOp):
    def set_quant_axis(self):
        self.quant_axis = 0
        self.inputs = {'X': np.random.random((30, 15)).astype("float32"), }


class TestFakeChannelWiseQuantizeOp3(TestFakeChannelWiseQuantizeOp):
    def set_quant_axis(self):
        self.quant_axis = 1
        self.inputs = {'X': np.random.random((30, 15)).astype("float32"), }


class TestFakeQuantizeRangeAbsMaxOp(OpTest):
    def setUp(self):
        self.op_type = "fake_quantize_range_abs_max"
        self.attrs = {
            'bit_length': int(5),
            'window_size': int(1),
            'is_test': False
        }
        x = (np.random.random((8, 16, 7, 7)) - 0.5) * 10
        x = x.astype("float32")
        self.inputs = {
            'X': x,
            'Iter': np.zeros(1).astype("int64"),
            'InScale': np.zeros(1).astype("float32")
        }
        scale = np.max(np.abs(self.inputs['X'])).astype("float32")

        out_scales = np.zeros(self.attrs['window_size']).astype("float32")
        out_scales[0] = scale
        self.outputs = {
            'Out': np.round(self.inputs['X'] / scale * (
                (1 << (self.attrs['bit_length'] - 1)) - 1)),
            'OutScale': scale,
            'OutScales': out_scales,
        }

    def test_check_output(self):
        self.check_output()


class TestMovingAverageAbsMaxScaleOp(OpTest):
    def setUp(self):
        self.op_type = "moving_average_abs_max_scale"
        self.attrs = {'moving_rate': float(0.9), 'is_test': False}
        accum = np.zeros(1).astype("float32")
        accum[0] = 1
        state = np.zeros(1).astype("float32")
        state[0] = 1
        self.inputs = {
            'X': np.random.random((8, 16, 7, 7)).astype("float32"),
            'InAccum': accum,
            'InState': state,
        }

        out_accum = np.zeros(1).astype("float32")
        out_state = np.zeros(1).astype("float32")
        out_scale = np.zeros(1).astype("float32")
        out_accum[0] = self.attrs['moving_rate'] * accum[0] + np.max(
            np.abs(self.inputs['X'])).astype("float32")
        out_state[0] = self.attrs['moving_rate'] * state[0] + 1
        out_scale = out_accum / out_state
        self.outputs = {
            'OutAccum': out_accum,
            'OutState': out_state,
            'OutScale': out_scale,
        }

    def test_check_output(self):
        self.check_output()


class TestFakeQuantizeRangeAbsMaxOp2(OpTest):
    def setUp(self):
        self.op_type = "fake_quantize_range_abs_max"
        self.attrs = {
            'bit_length': int(8),
            'window_size': int(1),
            'is_test': True
        }
        x = (np.random.random((8, 16, 7, 7)) - 0.5) * 10
        x = x.astype("float32")
        scale = np.array([np.max(np.abs(x)).astype("float32") - 1.0])
        out_scales = np.zeros(self.attrs['window_size']).astype("float32")
        out_scales[0] = scale
        self.inputs = {
            'X': x,
            'Iter': np.zeros(1).astype("int64"),
            'InScale': scale.astype("float32")
        }
        xs = np.clip(x, -scale, scale)
        qs = np.round(xs / scale * ((1 << (self.attrs['bit_length'] - 1)) - 1))
        self.outputs = {
            'Out': qs,
            'OutScale': scale.astype("float32"),
            'OutScales': out_scales,
        }

    def test_check_output(self):
        self.check_output(no_check_set=set(['OutScale', 'OutScales']))


class TestMovingOpBase(OpTest):
    def setUp(self):
        self.init_type()
        self.attrs = {
            'bit_length': int(5),
            'moving_rate': float(0.9),
            'is_test': False
        }
        accum = np.zeros(1).astype("float32")
        accum[0] = 1
        state = np.zeros(1).astype("float32")
        state[0] = 1
        scale = np.zeros(1).astype("float32")
        scale[0] = 0.001
        self.inputs = {
            'X': np.random.random((8, 16, 7, 7)).astype("float32"),
            'InScale': scale,
            'InAccum': accum,
            'InState': state,
        }

        out_accum = np.zeros(1).astype("float32")
        out_state = np.zeros(1).astype("float32")
        out_scale = np.zeros(1).astype("float32")
        out_accum[0] = self.attrs['moving_rate'] * accum[0] + np.max(
            np.abs(self.inputs['X'])).astype("float32")
        out_state[0] = self.attrs['moving_rate'] * state[0] + 1
        out_scale = out_accum / out_state
        out_data = self.calc_output(out_scale)
        self.outputs = {
            'Out': out_data,
            'OutAccum': out_accum,
            'OutState': out_state,
            'OutScale': out_scale,
        }

    def init_type(self):
        self.op_type = "fake_quantize_moving_average_abs_max"

    def calc_output(self, out_scale):
        return np.round(self.inputs['X'] / out_scale * (
            (1 << (self.attrs['bit_length'] - 1)) - 1))

    def test_check_output(self):
        self.check_output()


class TestFakeQuantDequantMovingOp(TestMovingOpBase):
    def init_type(self):
        self.op_type = "fake_quantize_dequantize_moving_average_abs_max"

    def calc_output(self, out_scale):
        range_v = (1 << (self.attrs['bit_length'] - 1)) - 1
        return np.round(self.inputs['X'] / out_scale *
                        range_v) * out_scale / range_v

    def test_check_grad(self):
        x = self.inputs["X"]
        gradient = [np.ones(x.shape) / np.product(x.shape)]
        self.check_grad(["X"], "Out", user_defined_grads=gradient)


class TestFakeQuantDequantAbsOp(OpTest):
    def setUp(self):
        self.op_type = "fake_quantize_dequantize_abs_max"
        self.attrs = {'bit_length': 8}
        self.inputs = {'X': np.random.random((124, 240)).astype("float32"), }
        scale = np.max(np.abs(self.inputs['X'])).astype("float32")
        out_data = self.calc_output(scale)
        self.outputs = {
            'Out': out_data,
            'OutScale': np.array(scale).astype("float32"),
        }

    def calc_output(self, scale):
        range_v = (1 << (self.attrs['bit_length'] - 1)) - 1
        return np.round(self.inputs['X'] / scale * range_v) * scale / range_v

    def test_check_output(self):
        self.check_output()

    def test_check_grad(self):
        x = self.inputs["X"]
        gradient = [np.ones(x.shape) / np.product(x.shape)]
        self.check_grad(["X"], "Out", user_defined_grads=gradient)


if __name__ == "__main__":
    unittest.main()
