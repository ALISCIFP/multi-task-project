"""
Conll Model
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import time

import tensorflow.python.platform

import numpy as np
import tensorflow as tf

from tensorflow.models.rnn import rnn_cell
from tensorflow.models.rnn import seq2seq
from tensorflow.models.rnn import rnn
import conll_pos_reader as reader
import pdb


class Conll_Model(object):
    """Conll Model"""

    def __init__(self, is_training, config, pos_vocab):
        self.batch_size = batch_size = config.batch_size
        self.num_steps = num_steps = config.num_steps
        size = config.hidden_size
        vocab_size = config.vocab_size

        self._input_data = tf.placeholder(tf.int32, [batch_size, num_steps])
        # add input size - size of pos tags
        self._targets = tf.placeholder(tf.float32, [(batch_size*num_steps), pos_vocab])

        lstm_cell = rnn_cell.BasicLSTMCell(size, forget_bias=0.0)
        if is_training and config.keep_prob < 1:
            lstm_cell = rnn_cell.DropoutWrapper(
                lstm_cell, output_keep_prob=config.keep_prob)
        cell = rnn_cell.MultiRNNCell([lstm_cell] * config.num_layers)

        self._initial_state = cell.zero_state(batch_size, tf.float32)

        with tf.device("/cpu:0"):
            embedding = tf.get_variable("embedding", [vocab_size, size])
            inputs = tf.nn.embedding_lookup(embedding, self._input_data)

        if is_training and config.keep_prob < 1:
            inputs = tf.nn.dropout(inputs, config.keep_prob)

        outputs = []
        output = []
        state = self._initial_state
        with tf.variable_scope("RNN"):
            for time_step in range(num_steps):
                if time_step > 0: tf.get_variable_scope().reuse_variables()
                (cell_output, state) = cell(inputs[:, time_step, :], state)
                outputs.append(cell_output)

        # inputs = [tf.squeeze(input_, [1])
        #           for input_ in tf.split(1, num_steps, inputs)]
        # outputs, state = rnn.rnn(cell,
        #                          inputs, initial_state=self._initial_state)

        output = tf.reshape(tf.concat(1, outputs), [-1, size])
        softmax_w = tf.get_variable("softmax_w", [size, pos_vocab])
        softmax_b = tf.get_variable("softmax_b", [pos_vocab])
        logits = tf.matmul(output, softmax_w) + softmax_b
        loss = tf.reduce_mean(
            tf.nn.softmax_cross_entropy_with_logits(
                logits, self._targets))
        (_, int_targets) = tf.nn.top_k(self._targets, 1)
        (_, int_predictions) = tf.nn.top_k(logits,1)
        num_true = tf.reduce_sum(tf.cast(tf.equal(int_targets, int_predictions), tf.float32))
        self._cost = cost = loss
        self._final_state = state
        self._accuracy = num_true / (num_steps*batch_size)

        if not is_training:
            return

        self._lr = tf.Variable(0.0, trainable=False)
        tvars = tf.trainable_variables()
        grads, _ = tf.clip_by_global_norm(tf.gradients(cost, tvars),
                                          config.max_grad_norm)
        optimizer = tf.train.GradientDescentOptimizer(self.lr)
        self._train_op = optimizer.apply_gradients(zip(grads, tvars))

    def assign_lr(self, session, lr_value):
        session.run(tf.assign(self.lr, lr_value))

    @property
    def input_data(self):
        return self._input_data

    @property
    def targets(self):
        return self._targets

    @property
    def initial_state(self):
        return self._initial_state

    @property
    def cost(self):
        return self._cost

    @property
    def final_state(self):
        return self._final_state

    @property
    def lr(self):
        return self._lr

    @property
    def train_op(self):
        return self._train_op

    @property
    def accuracy(self):
        return self._accuracy

class Config(object):

    """Configuration for the network"""
    init_scale = 0.1
    learning_rate = 1.0
    max_grad_norm = 5
    num_layers = 2
    num_steps = 20
    hidden_size = 200
    max_epoch = 4
    max_max_epoch = 20
    keep_prob = 1.0
    lr_decay = 0.5
    batch_size = 20
    vocab_size = 20000

def run_epoch(session, m, words, pos, eval_op, pos_vocab, verbose=False):

    """Runs the model on the given data."""
    epoch_size = ((len(words) // m.batch_size) - 1) // m.num_steps
    start_time = time.time()
    costs = 0.0
    iters = 0
    accuracies = 0.0
    state = m.initial_state.eval()
    for step, (x, y) in enumerate(reader._create_batches(words, pos, m.batch_size,
                                                         m.num_steps, pos_vocab)):
        cost, state, accuracy, _ = session.run([m.cost, m.final_state, m.accuracy,  eval_op],
                                               {m.input_data: x,
                                               m.targets: y,
                                               m.initial_state: state})
        costs += cost
        iters += 1
        accuracies += accuracy

        if verbose and step % (epoch_size // 10) == 10:
            print("cost: %3f, total cost: %3f" % (cost, costs))
    return (costs / iters), (accuracies / iters)

def main(unused_args):

    """Main"""
    config = Config()
    raw_data = reader._raw_x_y_data(
        '/Users/jonathangodwin/project/data/', config.num_steps)
    words_t, pos_t, words_v, pos_v, word_vocab, pos_vocab = raw_data

    with tf.Graph().as_default(), tf.Session() as session:
        initializer = tf.random_uniform_initializer(-config.init_scale,
                                                    config.init_scale)

        with tf.variable_scope("model", reuse=None, initializer=initializer):
            m = Conll_Model(is_training=True, config=config, pos_vocab=pos_vocab)
        with tf.variable_scope("model", reuse=True, initializer=initializer):
            mvalid = Conll_Model(is_training=False, config=config, pos_vocab=pos_vocab)

        tf.initialize_all_variables().run()

        for i in range(config.max_max_epoch):
            lr_decay = config.lr_decay ** max(i - config.max_epoch, 0.0)
            m.assign_lr(session, config.learning_rate * lr_decay)

            print("Epoch: %d Learning rate: %.3f" % (i + 1, session.run(m.lr)))
            mean_loss, mean_accuracy = run_epoch(session, m, words_t, pos_t, m.train_op,
                                                 pos_vocab, verbose=True)
            print("Epoch: %d Training mean loss: %.3f, accuracy: %.3f"
                  % (i + 1, mean_loss, mean_accuracy))
            valid_loss, valid_accuracy = run_epoch(session, mvalid, words_v, pos_v, tf.no_op(),
                                                   pos_vocab, verbose=False)
            print("Epoch: %d Validation mean loss %.3f, accuracy: %.3f"
                  % (i + 1, valid_loss, valid_accuracy))


if __name__ == "__main__":
    tf.app.run()
