from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import math
import time
import random

import tensorflow as tf
import tensorflow.python.platform

from tensorflow.models.rnn import rnn_cell
from tensorflow.models.rnn import rnn

import lm_model_reader as reader
import numpy as np
import pdb
from main_graph import Shared_Model

import saveload

def run_epoch(session, m, words, pos, chunk, pos_vocab_size, chunk_vocab_size, vocab_size, num_steps,
              verbose=False, valid=False, model_type='JOINT'):
    """Runs the model on the given data."""
    epoch_size = ((len(words) // m.batch_size) + 1)
    start_time = time.time()
    comb_loss = 0.0
    pos_total_loss = 0.0
    chunk_total_loss = 0.0
    lm_total_loss = 0.0
    iters = 0
    accuracy = 0.0
    pos_predictions = []
    pos_true = []
    chunk_predictions = []
    chunk_true = []
    lm_predictions = []
    lm_true = []

    for step, (x, y_pos, y_chunk, y_lm) in enumerate(reader.create_batches(words, pos, chunk, m.batch_size,
                                               m.num_steps, pos_vocab_size, chunk_vocab_size, vocab_size)):

        if model_type == 'POS':
            if valid:
                eval_op = tf.no_op()
            else:
                eval_op = m.pos_op
        elif model_type == 'CHUNK':
            if valid:
                eval_op = tf.no_op()
            else:
                eval_op = m.chunk_op
        elif model_type == 'LM':
            if valid:
                eval_op = tf.no_op()
            else:
                eval_op = m.lm_op
        else:
            if valid:
                eval_op = tf.no_op()
            else:
                eval_op = m.joint_op


        joint_loss, _, pos_int_pred, chunk_int_pred, lm_int_pred, pos_int_true, \
            chunk_int_true, lm_int_true, pos_loss, chunk_loss, lm_loss = \
            session.run([m.joint_loss, eval_op, m.pos_int_pred,
                         m.chunk_int_pred, m.lm_int_pred, m.pos_int_targ, m.chunk_int_targ,
                         m.lm_int_targ, m.pos_loss, m.chunk_loss, m.lm_loss],
                        {m.input_data: x,
                         m.pos_targets: y_pos,
                         m.chunk_targets: y_chunk,
                         m.lm_targets: y_lm,
                         m.gold_embed: 0})

        comb_loss += joint_loss
        chunk_total_loss += chunk_loss
        pos_total_loss += pos_loss
        lm_total_loss += lm_loss
        iters += 1

        if verbose and step % 10 == 0:
            if model_type == 'POS':
                costs = pos_total_loss
                cost = pos_loss
            elif model_type == 'CHUNK':
                costs = chunk_total_loss
                cost = chunk_loss
            elif model_type == 'LM':
                costs = lm_total_loss
                cost = lm_loss
            else:
                costs = comb_loss
                cost = joint_loss
            print("Type: %s,cost: %3f, step: %3f" % (model_type, cost, step))

        pos_int_pred = np.reshape(pos_int_pred, [m.batch_size, m.num_steps])
        pos_int_true = np.reshape(pos_int_true, [m.batch_size, m.num_steps])
        pos_predictions.append(pos_int_pred)
        pos_true.append(pos_int_true)

        chunk_int_pred = np.reshape(chunk_int_pred, [m.batch_size, m.num_steps])
        chunk_int_true = np.reshape(chunk_int_true, [m.batch_size, m.num_steps])
        chunk_predictions.append(chunk_int_pred)
        chunk_true.append(chunk_int_true)

        lm_int_pred = np.reshape(lm_int_pred, [m.batch_size, m.num_steps])
        lm_int_true = np.reshape(lm_int_true, [m.batch_size, m.num_steps])
        lm_predictions.append(lm_int_pred)
        lm_true.append(lm_int_true)

    return (comb_loss / iters), pos_predictions, chunk_predictions, lm_predictions, \
        pos_true, chunk_true, lm_true, (pos_total_loss / iters), \
        (chunk_total_loss / iters), (lm_total_loss / iters)
