# pylint: skip-file

"""
 Copyright (c) 2018 Intel Corporation
 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at
      http://www.apache.org/licenses/LICENSE-2.0
 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
"""

import os
import tempfile
import unittest

from builtins import range

import caffe
import numpy as np


def python_net_file():
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
        f.write("""name: 'push_loss_layer_test_net'
                   force_backward: true
                   layer { name: "detections" type: "Input" top: "detections"
                           input_param { shape { dim: 1 dim: 1 dim: 2 dim: 11 } } }
                   layer { name: "anchor1" type: "Input" top: "anchor1"
                           input_param { shape { dim: 2 dim: 5 dim: 3 dim: 4 } } }
                   layer { name: "anchor2" type: "Input" top: "anchor2"
                           input_param { shape { dim: 2 dim: 5 dim: 3 dim: 4 } } }
                   layer { type: 'Python' name: 'push_loss' bottom: 'detections'
                           bottom: 'anchor1' bottom: 'anchor2' top: 'push_loss_value'
                           python_param { module: 'caffe.custom_layers.push_loss_layer'
                                          layer: 'PushLossLayer'
                                          param_str: '{ "num_anchors": 2, "valid_action_ids": [0, 1], "margin": 1.0}' } }""")
        return f.name


@unittest.skipIf('Python' not in caffe.layer_type_list(), 'Caffe built without Python layer support')
class TestPushLossLayer(unittest.TestCase):
    def setUp(self):
        net_file = python_net_file()
        self.net = caffe.Net(net_file, caffe.TRAIN)
        os.remove(net_file)

        self.detections = np.array([[0, 1, 0, 0, 1, 1, 0, 0, 0, 2, 1],
                                    [1, 1, 0, 0, 1, 1, 1, 1, 1, 3, 2]], dtype=np.float32)

        anchor1 = np.random.normal(size=[2, 5, 3, 4])
        anchor1 /= np.sqrt(np.sum(np.square(anchor1), axis=1, keepdims=True))
        anchor2 = np.random.normal(size=[2, 5, 3, 4])
        anchor2 /= np.sqrt(np.sum(np.square(anchor2), axis=1, keepdims=True))
        self.anchors = [anchor1, anchor2]

    def test_forward(self):
        embeddings = []
        for i in range(2):
            detection = self.detections[i]
            item = int(detection[0])
            anchor_id = int(detection[6])
            x_pos = int(detection[9])
            y_pos = int(detection[10])

            embeddings.append(self.anchors[anchor_id][item, :, y_pos, x_pos])

        loss = np.sum(embeddings[0] * embeddings[1])
        trg_loss_value = loss if loss > 0.0 else 0.0

        self.net.blobs['detections'].data[...] = self.detections
        self.net.blobs['anchor1'].data[...] = self.anchors[0]
        self.net.blobs['anchor2'].data[...] = self.anchors[1]

        net_outputs = self.net.forward()
        predicted_loss_value = net_outputs['push_loss_value']
        self.assertEqual(len(predicted_loss_value), 1)

        self.assertAlmostEqual(predicted_loss_value[0], trg_loss_value, places=5)
