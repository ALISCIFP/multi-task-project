from __future__ import division
from __future__ import print_function

import tensorflow as tf
import tensorflow.python.platform

import model_reader as reader
import numpy as np
import pdb
import pandas as pd
from graph import Shared_Model
from run_epoch import run_epoch

class Config(object):
    """Configuration for the network"""
    init_scale = 0.1
    learning_rate = 0.001
    max_grad_norm = 5
    num_steps = 20
    encoder_size = 200
    pos_decoder_size = 200
    chunk_decoder_size = 200
    max_epoch = 50
    keep_prob = 0.5
    batch_size = 64
    vocab_size = 20000
    num_pos_tags = 45
    num_chunk_tags = 23

def main(unused_args):
    """Main."""
    config = Config()
    raw_data = reader.raw_x_y_data(
        '/Users/jonathangodwin/project/data/', config.num_steps)
    words_t, pos_t, chunk_t, words_v, \
        pos_v, chunk_v, word_to_id, pos_to_id, \
        chunk_to_id, words_test, pos_test, chunk_test, \
        words_c, pos_c, chunk_c = raw_data

    config.num_pos_tags = len(pos_to_id)
    config.num_chunk_tags = len(chunk_to_id)


    with tf.Graph().as_default(), tf.Session() as session:
        initializer = tf.random_uniform_initializer(-config.init_scale,
                                                    config.init_scale)

        with tf.variable_scope("hyp_model", reuse=None, initializer=initializer):
            m = Shared_Model(is_training=True, config=config)
        with tf.variable_scope("hyp_model", reuse=True, initializer=initializer):
            mvalid = Shared_Model(is_training=False, config=config)
        with tf.variable_scope("fin_model", reuse=None, initializer=initializer):
            mTrain = Shared_Model(is_training=True, config=config)
        with tf.variable_scope("fin_model", reuse=True, initializer=initializer):
            mTest = Shared_Model(is_training=False, config=config)

        tf.initialize_all_variables().run()
        best_epoch = [0, 100000]
        print('finding best epoch parameter')
        for i in range(config.max_epoch):
            print("Epoch: %d" % (i + 1))

            mean_loss, posp_t, chunkp_t, post_t, chunkt_t = \
                run_epoch(session, m,
                          words_t, pos_t, chunk_t,
                          config.num_pos_tags, config.num_chunk_tags,
                          verbose=True)
            train_file = open('train_loss.txt', 'a')
            print(mean_loss, file=train_file)

            train_file.close()
            valid_loss, posp_v, chunkp_v, post_v, chunkt_v = \
                run_epoch(session, mvalid, words_v, pos_v, chunk_v,
                          config.num_pos_tags, config.num_chunk_tags,
                          verbose=True, valid=True)
            valid_file = open('valid_loss.txt', 'a')
            print(valid_loss, file=valid_file)
            if(valid_loss < best_epoch[1]):
                best_epoch = [i+1, valid_loss]
            valid_file.close()

        print('Train Given Best Epoch Parameter')
        for i in range(best_epoch[0]):
            print("Epoch: %d" % (i + 1))
            mean_loss, posp_c, chunkp_c, post_c, chunkt_c = \
                run_epoch(session, mTrain,
                          words_c, pos_c, chunk_c,
                          config.num_pos_tags, config.num_chunk_tags,
                          verbose=True)
            train_file = open('train_loss_fin.txt', 'a')
            print(mean_loss, file=train_file)
            train_file.close()

        print('Getting Testing Predictions')
        mean_test_loss, posp_test, chunkp_test, post_test, chunkt_test = \
            run_epoch(session, mTest,
                      words_test, pos_test, chunk_test,
                      config.num_pos_tags, config.num_chunk_tags,
                      verbose=True, valid=True)

        print('Writing Predictions')
        # prediction reshaping
        posp_t = reader._res_to_list(posp_t, config.batch_size, config.num_steps,
                                     pos_to_id, len(words_t))
        posp_v = reader._res_to_list(posp_v, config.batch_size, config.num_steps,
                                     pos_to_id, len(words_v))
        posp_c = reader._res_to_list(posp_c, config.batch_size, config.num_steps,
                                     pos_to_id, len(words_c))
        posp_test = reader._res_to_list(posp_test, config.batch_size, config.num_steps,
                                        pos_to_id, len(words_test))
        chunkp_t = reader._res_to_list(chunkp_t, config.batch_size,
                                       config.num_steps, chunk_to_id, len(words_t))
        chunkp_v = reader._res_to_list(chunkp_v, config.batch_size,
                                       config.num_steps, chunk_to_id, len(words_v))
        chunkp_c = reader._res_to_list(chunkp_c, config.batch_size,
                                       config.num_steps, chunk_to_id, len(words_c))
        chunkp_test = reader._res_to_list(chunkp_test, config.batch_size, config.num_steps,
                                          chunk_to_id, len(words_test))




        print('saving')
        train_custom = pd.read_csv('/Users/jonathangodwin/project/data/train_custom.txt', sep= ' ',header=None).as_matrix()
        valid_custom = pd.read_csv('/Users/jonathangodwin/project/data/val_custom.txt', sep= ' ',header=None).as_matrix()
        combined = pd.read_csv('/Users/jonathangodwin/project/data/train.txt', sep= ' ',header=None).as_matrix()
        test_data = pd.read_csv('/Users/jonathangodwin/project/data/test.txt', sep= ' ',header=None).as_matrix()

        chunk_pred_train = np.concatenate((train_custom, chunkp_t), axis=1)
        chunk_pred_val = np.concatenate((valid_custom, chunkp_v), axis=1)
        pdb.set_trace()
        chunk_pred_c = np.concatenate((combined, chunkp_c), axis=1)
        chunk_pred_test = np.concatenate((test_data, chunkp_test), axis=1)
        pos_pred_train = np.concatenate((train_custom, posp_t), axis=1)
        pos_pred_val = np.concatenate((valid_custom, posp_v), axis=1)
        pos_pred_c = np.concatenate((combined, posp_c), axis=1)
        pos_pred_test = np.concatenate((test_data, posp_test), axis=1)

        np.savetxt('../../data/current_outcome/chunk_pred_train.txt',
                   chunk_pred_train, fmt='%s')
        np.savetxt('../../data/current_outcome/chunk_pred_val.txt',
                   chunk_pred_val, fmt='%s')
        np.savetxt('../../data/current_outcome/chunk_pred_combined.txt',
                   chunk_pred_c, fmt='%s')
        np.savetxt('../../data/current_outcome/chunk_pred_test.txt',
                   chunk_pred_test, fmt='%s')
        np.savetxt('../../data/current_outcome/pos_pred_train.txt',
                   pos_pred_train, fmt='%s')
        np.savetxt('../../data/current_outcome/pos_pred_val.txt',
                   pos_pred_val, fmt='%s')
        np.savetxt('../../data/current_outcome/pos_pred_combined.txt',
                   pos_pred_c, fmt='%s')
        np.savetxt('../../data/current_outcome/pos_pred_test.txt',
                   pos_pred_test, fmt='%s')


if __name__ == "__main__":
    tf.app.run()
