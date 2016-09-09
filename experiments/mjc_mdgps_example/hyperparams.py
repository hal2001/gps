""" Hyperparameters for MJC peg insertion policy optimization. """
from __future__ import division

from datetime import datetime
import os.path

import numpy as np

from gps import __file__ as gps_filepath
from gps.agent.mjc.agent_mjc import AgentMuJoCo
from gps.algorithm.algorithm_mdgps import AlgorithmMDGPS
from gps.algorithm.cost.cost_fk import CostFK
from gps.algorithm.cost.cost_action import CostAction
from gps.algorithm.cost.cost_sum import CostSum
from gps.algorithm.cost.cost_utils import RAMP_FINAL_ONLY, evall1l2term
from gps.algorithm.dynamics.dynamics_lr_prior import DynamicsLRPrior
from gps.algorithm.dynamics.dynamics_prior_gmm import DynamicsPriorGMM
from gps.algorithm.traj_opt.traj_opt_lqr_python import TrajOptLQRPython
from gps.algorithm.policy_opt.policy_opt_caffe import PolicyOptCaffe
from gps.algorithm.policy.lin_gauss_init import init_lqr
from gps.algorithm.policy.policy_prior_gmm import PolicyPriorGMM
from gps.algorithm.policy.policy_prior import PolicyPrior
from gps.proto.gps_pb2 import JOINT_ANGLES, JOINT_VELOCITIES, \
        END_EFFECTOR_POINTS, END_EFFECTOR_POINT_VELOCITIES, ACTION
from gps.gui.config import generate_experiment_info


SENSOR_DIMS = {
    JOINT_ANGLES: 7,
    JOINT_VELOCITIES: 7,
    END_EFFECTOR_POINTS: 6,
    END_EFFECTOR_POINT_VELOCITIES: 6,
    ACTION: 7,
}

PR2_GAINS = np.array([3.09, 1.08, 0.393, 0.674, 0.111, 0.152, 0.098])

BASE_DIR = '/'.join(str.split(gps_filepath, '/')[:-2])
EXP_DIR = BASE_DIR + '/../experiments/mjc_mdgps_example/'

common = {
    'experiment_name': 'my_experiment' + '_' + \
            datetime.strftime(datetime.now(), '%m-%d-%y_%H-%M'),
    'conditions': 4,
    # 'conditions': 9,
}

agent = {
    'type': AgentMuJoCo,
    'filename': './mjc_models/pr2_arm3d.xml',
    'x0': np.concatenate([np.array([0.1, 0.1, -1.54, -1.7, 1.54, -0.2, 0]),
                          np.zeros(7)]),
    'dt': 0.05,
    'substeps': 5,
    'conditions': common['conditions'],
    'randomly_sample_bodypos': False,
    'randomly_sample_x0': False,
    'sampling_range_bodypos': [np.array([-0.1,-0.1, 0.0]), np.array([0.1, 0.1, 0.0])], # Format is [lower_lim, upper_lim]
    'prohibited_ranges_bodypos':[[None, None, None, None]],
    'pos_body_idx': np.array([1]),
    # 'pos_body_offset': [np.array([-0.08, -0.08, 0])],
    # 'pos_body_offset': [np.array([-0.1, -0.1, 0]), np.array([-0.1, 0.1, 0]),
    #                     np.array([0.1, 0.1, 0]), np.array([0.1, -0.1, 0])],
    'pos_body_offset': [np.array([-0.05, -0.05, -0.05]), np.array([-0.05, 0.05, 0.05]),
                         np.array([0.05, -0.05, 0.05]), np.array([0.05, 0.05, 0.05])],
    # 'pos_body_offset': [np.array([-0.1, -0.1, 0]), np.array([-0.1, 0, 0]), np.array([-0.1, 0.1, 0]),
    #                     np.array([0, -0.1, 0]), np.array([0, 0, 0]), np.array([0, 0.1, 0]),
    #                     np.array([0.1, 0.1, 0]), np.array([0.1, 0, 0]), np.array([0.1, -0.1, 0])],
    # 'pos_body_offset': [np.array([-0.05, -0.05, 0]), np.array([-0.05, 0, 0]), np.array([-0.05, 0.05, 0]),
    #             np.array([0, -0.05, 0]), np.array([0, 0, 0]), np.array([0, 0.05, 0]),
    #             np.array([0.05, 0.05, 0]), np.array([0.05, 0, 0]), np.array([0.05, -0.05, 0])],
    'T': 100,
    'sensor_dims': SENSOR_DIMS,
    'state_include': [JOINT_ANGLES, JOINT_VELOCITIES, END_EFFECTOR_POINTS,
                      END_EFFECTOR_POINT_VELOCITIES],
    'obs_include': [JOINT_ANGLES, JOINT_VELOCITIES, END_EFFECTOR_POINTS,
                    END_EFFECTOR_POINT_VELOCITIES],
    'camera_pos': np.array([0., 0., 2., 0., 0.2, 0.5]),
}

algorithm = {
    'type': AlgorithmMDGPS,
    'conditions': common['conditions'],
    'iterations': 12,
    'max_ent_traj': 1.0,
    'kl_step': 1.0,
    'min_step_mult': 0.05,
    'max_step_mult': 3.0,
    'policy_sample_mode': 'replace',
    'target_end_effector': np.array([0.0, 0.3, -0.5, 0.0, 0.3, -0.2]),
}

algorithm['init_traj_distr'] = {
    'type': init_lqr,
    'init_gains':  1.0 / PR2_GAINS,
    'init_acc': np.zeros(SENSOR_DIMS[ACTION]),
    'init_var': 1.0,
    'stiffness': 1.0,
    'stiffness_vel': 0.5,
    'final_weight': 50.0,
    'dt': agent['dt'],
    'T': agent['T'],
}

torque_cost = {
    'type': CostAction,
    'wu': 1e-3 / PR2_GAINS,
}

fk_cost = {
    'type': CostFK,
    'target_end_effector': np.array([0.0, 0.3, -0.5, 0.0, 0.3, -0.2]),
    'wp': np.array([2, 2, 1, 2, 2, 1]),
    'l1': 0.1,
    'l2': 10.0,
    'alpha': 1e-5,
    'evalnorm': evall1l2term,
}

# Create second cost function for last step only.
final_cost = {
    'type': CostFK,
    'ramp_option': RAMP_FINAL_ONLY,
    'target_end_effector': fk_cost['target_end_effector'],
    'wp': fk_cost['wp'],
    'l1': 1.0,
    'l2': 0.0,
    'alpha': 1e-5,
    'wp_final_multiplier': 10.0,
    'evalnorm': evall1l2term,
}

algorithm['cost'] = {
    'type': CostSum,
    'costs': [torque_cost, fk_cost, final_cost],
    'weights': [1000.0, 1000.0, 1000.0],
}

algorithm['dynamics'] = {
    'type': DynamicsLRPrior,
    'regularization': 1e-6,
    'prior': {
        'type': DynamicsPriorGMM,
        'max_clusters': 20,
        'min_samples_per_cluster': 40,
        'max_samples': 20,
    },
}

algorithm['traj_opt'] = {
    'type': TrajOptLQRPython,
}

algorithm['policy_opt'] = {
    'type': PolicyOptCaffe,
    'iterations': 4000,
    'weights_file_prefix': EXP_DIR + 'policy',
}

algorithm['policy_prior'] = {
    'type': PolicyPriorGMM,
    'max_clusters': 20,
    'min_samples_per_cluster': 40,
    'max_samples': 20,
}

config = {
    'iterations': algorithm['iterations'],
    'num_samples': 5,
    'verbose_trials': 1,
    'verbose_policy_trials': 1,
    'agent': agent,
    'gui_on': True,
}
