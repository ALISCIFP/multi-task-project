from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf

import pdb

def shared_layer(input_data, config, is_training):
    """Build the model to decoding

    Args:
        input_data = size batch_size X num_steps X embedding size

    Returns:
        output units
    """

    if config.bidirectional == True:
        if config.lstm == True:
            cell_fw = tf.nn.rnn_cell.BasicLSTMCell(config.encoder_size, forget_bias = 1.0)
            cell_bw = tf.nn.rnn_cell.BasicLSTMCell(config.encoder_size, forget_bias = 1.0)
        else:
            cell_fw = tf.nn.rnn_cell.GRUCell(config.encoder_size)
            cell_bw = tf.nn.rnn_cell.GRUCell(config.encoder_size)

        inputs = [tf.squeeze(input_, [1])
                  for input_ in tf.split(1, config.num_steps, input_data)]

        if is_training and config.keep_prob < 1:
            cell_fw = tf.nn.rnn_cell.DropoutWrapper(
                cell_fw, output_keep_prob=config.keep_prob)
            cell_bw = tf.nn.rnn_cell.DropoutWrapper(
                cell_bw, output_keep_prob=config.keep_prob)


        cell_fw = tf.nn.rnn_cell.MultiRNNCell([cell_fw] * config.num_shared_layers)
        cell_bw = tf.nn.rnn_cell.MultiRNNCell([cell_bw] * config.num_shared_layers)

        initial_state_fw = cell_fw.zero_state(config.batch_size, tf.float32)
        initial_state_bw = cell_bw.zero_state(config.batch_size, tf.float32)

        encoder_outputs, _, _ = tf.nn.bidirectional_rnn(cell_fw, cell_bw, inputs,
                                              initial_state_fw=initial_state_fw,
                                              initial_state_bw=initial_state_bw,
                                              scope="encoder_rnn")


    else:
        if config.lstm == True:
            cell = tf.nn.rnn_cell.BasicLSTMCell(config.encoder_size)
        else:
            cell = tf.nn.rnn_cell.GRUCell(config.encoder_size)

        inputs = [tf.squeeze(input_, [1])
                  for input_ in tf.split(1, config.num_steps, input_data)]

        if is_training and config.keep_prob < 1:
            cell = tf.nn.rnn_cell.DropoutWrapper(
                cell, output_keep_prob=config.keep_prob)

        cell = tf.nn.rnn_cell.MultiRNNCell([cell] * config.num_shared_layers)

        initial_state = cell.zero_state(config.batch_size, tf.float32)

        encoder_outputs, encoder_states = rnn.rnn(cell, inputs,
                                                  initial_state=initial_state,
                                                  scope="encoder_rnn")

    return encoder_outputs
