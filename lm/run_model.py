from __future__ import division
from __future__ import print_function

import tensorflow as tf
import tensorflow.python.platform

import model_reader as reader
import numpy as np
import pdb
#import pandas as pd
from graph import Shared_Model
from run_epoch import run_epoch
import argparse
import saveload
import run_epoch_random
import time


class Config(object):
    def __init__(self, num_steps, encoder_size, pos_decoder_size, chunk_decoder_size,
    dropout, batch_size, pos_embedding_size, num_shared_layers, num_private_layers, chunk_embedding_size,
    lm_decoder_size, bidirectional, lstm, mix_percent, max_epoch):
        """Configuration for the network"""
        self.init_scale = 0.1 # initialisation scale
        self.learning_rate = 0.001 # learning_rate (if you are using SGD)
        self.max_grad_norm = 5 # for gradient clipping
        self.num_steps = int(num_steps) # length of sequence
        self.word_embedding_size = 300 # size of the embedding (consistent with glove)
        self.encoder_size = int(encoder_size) # first layer
        self.pos_decoder_size = int(pos_decoder_size) # second layer
        self.chunk_decoder_size = int(chunk_decoder_size) # second layer
        self.lm_decoder_size = int(lm_decoder_size) # second layer
        self.max_epoch = int(max_epoch) # maximum number of epochs
        self.keep_prob = float(dropout) # for dropout
        self.batch_size = int(batch_size) # number of sequence
        self.pos_embedding_size = int(pos_embedding_size)
        self.num_shared_layers = int(num_shared_layers)
        self.num_private_layers = int(num_private_layers)
        self.argmax = 0
        self.chunk_embedding_size = int(chunk_embedding_size)
        self.lm_decoder_size = int(lm_decoder_size)
        self.random_mix = True
        self.ptb = True
        self.lstm = lstm
        self.bidirectional = bidirectional
        self.mix_percent = mix_percent

def main(model_type, dataset_path, ptb_path, save_path,
    num_steps, encoder_size, pos_decoder_size, chunk_decoder_size, dropout,
    batch_size, pos_embedding_size, num_shared_layers, num_private_layers, chunk_embedding_size,
    lm_decoder_size, bidirectional, lstm, write_to_file, mix_percent,glove_path,max_epoch,embedding=False, test=False):

    """Main."""
    config = Config(num_steps, encoder_size, pos_decoder_size, chunk_decoder_size, dropout,
    batch_size, pos_embedding_size, num_shared_layers, num_private_layers, chunk_embedding_size,
    lm_decoder_size, bidirectional, lstm, mix_percent, max_epoch)

    raw_data_path = dataset_path + '/data'
    raw_data = reader.raw_x_y_data(
        raw_data_path, ptb_path + '/data', num_steps, embedding, glove_path)

    words_t, pos_t, chunk_t, words_v, \
        pos_v, chunk_v, word_to_id, pos_to_id, \
        chunk_to_id, words_test, pos_test, chunk_test, \
        words_c, pos_c, chunk_c, words_ptb, pos_ptb, chunk_ptb, word_embedding = raw_data

    num_pos_tags = len(pos_to_id)
    num_chunk_tags = len(chunk_to_id)
    vocab_size = len(word_to_id)

    train_lengths = [len(s) for s in words_t]
    validation_lengths = [len(s) for s in words_v]
    test_lengths = [len(s) for s in words_test]
    ptb_lengths = [len(s) for s in words_ptb]
    combined_lengths = [len(s) for s in words_c]

    # num_steps = np.max([np.max([len(s) for s in words_t]),
    #                     np.max([len(s) for s in words_ptb]),
    #                     np.max([len(s) for s in words_v]),
    #                     np.max([len(s) for s in words_test])])

    # Create an empty array to hold [epoch number, loss]
    if test==False:
        best_epoch = [0, 0.0]
    else:
        best_epoch = [max_epoch, 0.0]

    print('constructing word embedding')

    if embedding==True:
        word_embedding = np.float32(word_embedding)
    else:
        word_embedding = np.float32((np.random.rand(vocab_size, config.word_embedding_size)-0.5)*config.init_scale)

    if test==False:
        with tf.Graph().as_default(), tf.Session() as session:
            print('building models')
            initializer = tf.random_uniform_initializer(-config.init_scale,
                                                        config.init_scale)

            # model to train hyperparameters on
            with tf.variable_scope("hyp_model", reuse=None, initializer=initializer):
                m = Shared_Model(is_training=True, config=config, num_pos_tags=num_pos_tags,
                num_chunk_tags=num_chunk_tags, vocab_size=vocab_size, num_steps=num_steps)

            with tf.variable_scope("hyp_model", reuse=True, initializer=initializer):
                mValid = Shared_Model(is_training=False, config=config, num_pos_tags=num_pos_tags,
                num_chunk_tags=num_chunk_tags, vocab_size=vocab_size, num_steps=num_steps)


            print('initialising most variables')

            tf.initialize_all_variables().run()

            print('initialising word embeddings')
            session.run(m.embedding_init, feed_dict={m.embedding_placeholder: word_embedding})
            session.run(mValid.embedding_init, feed_dict={mValid.embedding_placeholder: word_embedding})

            print('finding best epoch parameter')
            # ====================================
            # Create vectors for training results
            # ====================================

            # Create empty vectors for loss
            train_loss_stats = np.array([])
            train_pos_loss_stats = np.array([])
            train_chunk_loss_stats = np.array([])
            train_lm_loss_stats = np.array([])

            # Create empty vectors for accuracy
            train_pos_stats = np.array([])
            train_chunk_stats = np.array([])
            train_lm_stats = np.array([])

            # ====================================
            # Create vectors for validation results
            # ====================================
            # Create empty vectors for loss
            valid_loss_stats = np.array([])
            valid_pos_loss_stats = np.array([])
            valid_chunk_loss_stats = np.array([])
            valid_lm_loss_stats = np.array([])

            # Create empty vectors for accuracy
            valid_pos_stats = np.array([])
            valid_chunk_stats = np.array([])
            valid_lm_stats = np.array([])

            for i in range(config.max_epoch):

                print("Epoch: %d" % (i + 1))
                if embedding == False:
                    if config.random_mix == False:
                        if config.ptb == True:
                            _, _, _, _, _, _, _, _, _, _ = \
                                run_epoch(session, m,
                                          words_ptb, pos_ptb, chunk_ptb,
                                          num_pos_tags, num_chunk_tags, vocab_size, num_steps,
                                          verbose=True, model_type='LM')

                        print(len(words_t))
                        mean_loss, posp_t, chunkp_t, lmp_t, post_t, chunkt_t, lmt_t, pos_loss, chunk_loss, lm_loss = \
                            run_epoch(session, m,
                                      words_t, pos_t, chunk_t,
                                      num_pos_tags, num_chunk_tags, vocab_size, num_steps,
                                      verbose=True, model_type=model_type)

                    else:
                        mean_loss, posp_t, chunkp_t, lmp_t, post_t, chunkt_t, lmt_t, pos_loss, chunk_loss, lm_loss = \
                            run_epoch_random.run_epoch(session, m,
                                      words_t, words_ptb, pos_t, pos_ptb, chunk_t, chunk_ptb,
                                      num_pos_tags, num_chunk_tags, vocab_size, num_steps,
                                      verbose=True, model_type=model_type)
                else:
                    if config.random_mix == False:
                        if config.ptb == True:
                            _, _, _, _, _, _, _, _, _, _ = \
                                run_epoch(session, m,
                                          words_ptb, pos_ptb, chunk_ptb,
                                          num_pos_tags, num_chunk_tags, vocab_size, num_steps,
                                          verbose=True, model_type='LM')


                        mean_loss, posp_t, chunkp_t, lmp_t, post_t, chunkt_t, lmt_t, pos_loss, chunk_loss, lm_loss = \
                            run_epoch(session, m,
                                      words_t, pos_t, chunk_t,
                                      num_pos_tags, num_chunk_tags, vocab_size, num_steps,
                                      verbose=True, model_type=model_type)

                    else:
                        mean_loss, posp_t, chunkp_t, lmp_t, post_t, chunkt_t, lmt_t, pos_loss, chunk_loss, lm_loss = \
                            run_epoch_random.run_epoch(session, m,
                                      words_t, words_ptb, pos_t, pos_ptb, chunk_t, chunk_ptb,
                                      num_pos_tags, num_chunk_tags, vocab_size, num_steps,
                                      verbose=True, model_type=model_type)


                print('epoch finished')
                # Save stats for charts
                train_loss_stats = np.append(train_loss_stats, mean_loss)
                train_pos_loss_stats = np.append(train_pos_loss_stats, pos_loss)
                train_chunk_loss_stats = np.append(train_chunk_loss_stats, chunk_loss)
                train_lm_loss_stats = np.append(train_lm_loss_stats, lm_loss)

                # find the accuracy
                print('finding accuracy')
                pos_acc = np.sum(np.array(posp_t).flatten() == np.array(post_t).flatten())/float(len(np.array(posp_t).flatten()))
                chunk_acc = np.sum(np.array(chunkp_t).flatten() == np.array(chunkt_t).flatten())/float(len(np.array(chunkp_t).flatten()))
                lm_acc = np.sum(np.array(lmp_t).flatten() == np.array(lmt_t).flatten())/float(len(np.array(lmp_t).flatten()))


                # add to array
                train_pos_stats = np.append(train_pos_stats, pos_acc)
                train_chunk_stats = np.append(train_chunk_stats, chunk_acc)
                train_lm_stats = np.append(train_lm_stats, lm_acc)

                # print for tracking
                print("Pos Training Accuracy After Epoch %d :  %3f" % (i+1, pos_acc))
                print("Chunk Training Accuracy After Epoch %d : %3f" % (i+1, chunk_acc))

                valid_loss, posp_v, chunkp_v, lmp_v, post_v, chunkt_v, lmt_v, pos_v_loss, chunk_v_loss, lm_v_loss = \
                    run_epoch(session, mValid, words_v, pos_v, chunk_v,
                              num_pos_tags, num_chunk_tags, vocab_size, num_steps,
                              verbose=True, valid=True, model_type=model_type)

                # Save loss for charts
                valid_loss_stats = np.append(valid_loss_stats, valid_loss)
                valid_pos_loss_stats = np.append(valid_pos_loss_stats, pos_v_loss)
                valid_chunk_loss_stats = np.append(valid_chunk_loss_stats, chunk_v_loss)
                valid_lm_loss_stats = np.append(valid_lm_loss_stats, lm_v_loss)

                # find accuracy
                pos_acc = np.sum(np.array(posp_v).flatten() == np.array(post_v).flatten())/float(len(np.array(posp_v).flatten()))
                chunk_acc = np.sum(np.array(chunkp_v).flatten() == np.array(chunkt_v).flatten())/float(len(np.array(chunkp_v).flatten()))
                lm_acc = np.sum(np.array(lmp_v).flatten() == np.array(lmt_v).flatten())/float(len(np.array(lmp_v).flatten()))

                print("Pos Validation Accuracy After Epoch %d :  %3f" % (i+1, pos_acc))
                print("Chunk Validation Accuracy After Epoch %d : %3f" % (i+1, chunk_acc))

                # add to stats
                valid_pos_stats = np.append(valid_pos_stats, pos_acc)
                valid_chunk_stats = np.append(valid_chunk_stats, chunk_acc)
                valid_lm_stats = np.append(valid_lm_stats, lm_acc)

                # update best parameters
                if(chunk_acc > best_epoch[1]):
                    best_epoch = [i+1, chunk_acc]

                if write_to_file ==True:
                    saveload.save(save_path + '/val_model.pkl', session)
                    #model_save_path = saver.save(session, save_path + '/val_model.ckpt')
                    print("Model saved in file: %s" % save_path)


            # get training predictions as list
            posp_t = reader._res_to_list(posp_t, config.batch_size,
                                         pos_to_id, len(words_t), train_lengths,  to_str=True)
            chunkp_t = reader._res_to_list(chunkp_t, config.batch_size,
                                           chunk_to_id, len(words_t), train_lengths, to_str=True)
            lmp_t = reader._res_to_list(lmp_t, config.batch_size,
                                             word_to_id, len(words_t), train_lengths, to_str=True)
            post_t = reader._res_to_list(post_t, config.batch_size,
                                         pos_to_id, len(words_t), train_lengths, to_str=True)
            chunkt_t = reader._res_to_list(chunkt_t, config.batch_size,
                                            chunk_to_id, len(words_t), train_lengths, to_str=True)
            lmt_t = reader._res_to_list(lmt_t, config.batch_size,
                                             word_to_id, len(words_t), train_lengths, to_str=True)


            # get predictions as list
            posp_v = reader._res_to_list(posp_v, config.batch_size,
                                         pos_to_id, len(words_v), validation_lengths, to_str=True)
            chunkp_v = reader._res_to_list(chunkp_v, config.batch_size,
                                            chunk_to_id, len(words_v), validation_lengths, to_str=True)
            lmp_v = reader._res_to_list(lmp_v, config.batch_size,
                                            word_to_id, len(words_v), validation_lengths, to_str=True)
            chunkt_v = reader._res_to_list(chunkt_v, config.batch_size,
                                            chunk_to_id, len(words_v), validation_lengths, to_str=True)
            post_v = reader._res_to_list(post_v, config.batch_size,
                                         pos_to_id, len(words_v), validation_lengths, to_str=True)
            lmt_v = reader._res_to_list(lmt_v, config.batch_size,
                                            word_to_id, len(words_v), validation_lengths, to_str=True)
            # Save loss & accuracy plots
            if write_to_file == True:
                np.savetxt(save_path + '/loss/valid_loss_stats.txt', valid_loss_stats)
                np.savetxt(save_path + '/loss/valid_pos_loss_stats.txt', valid_pos_loss_stats)
                np.savetxt(save_path + '/loss/valid_chunk_loss_stats.txt', valid_chunk_loss_stats)
                np.savetxt(save_path + '/loss/valid_lm_loss_stats.txt', valid_lm_loss_stats)
                np.savetxt(save_path + '/accuracy/valid_pos_stats.txt', valid_pos_stats)
                np.savetxt(save_path + '/accuracy/valid_chunk_stats.txt', valid_chunk_stats)
                np.savetxt(save_path + '/accuracy/valid_lm_stats.txt', valid_chunk_stats)

                np.savetxt(save_path + '/loss/train_loss_stats.txt', train_loss_stats)
                np.savetxt(save_path + '/loss/train_pos_loss_stats.txt', train_pos_loss_stats)
                np.savetxt(save_path + '/loss/train_chunk_loss_stats.txt', train_chunk_loss_stats)
                np.savetxt(save_path + '/loss/train_lm_loss_stats.txt', train_lm_loss_stats)
                np.savetxt(save_path + '/accuracy/train_pos_stats.txt', train_pos_stats)
                np.savetxt(save_path + '/accuracy/train_chunk_stats.txt', train_chunk_stats)
                np.savetxt(save_path + '/accuracy/train_lm_stats.txt', train_lm_stats)
                # model that trains, given hyper-parameters

    with tf.Graph().as_default(), tf.Session() as session:
        initializer = tf.random_uniform_initializer(-config.init_scale,
                                                    config.init_scale)

        with tf.variable_scope("final_model", reuse=None, initializer=initializer):
            mTrain = Shared_Model(is_training=True, config=config, num_pos_tags=num_pos_tags,
            num_chunk_tags=num_chunk_tags, vocab_size=vocab_size, num_steps=num_steps)

        with tf.variable_scope("final_model", reuse=True, initializer=initializer):
            mTest = Shared_Model(is_training=False, config=config, num_pos_tags=num_pos_tags,
            num_chunk_tags=num_chunk_tags, vocab_size=vocab_size, num_steps=num_steps)


        tf.initialize_all_variables().run()

        session.run(mTrain.embedding_init, feed_dict={mTrain.embedding_placeholder: word_embedding})
        session.run(mTest.embedding_init, feed_dict={mTest.embedding_placeholder: word_embedding})


        if write_to_file == True:

            # Train given epoch parameter
            if config.random_mix == False:
                print('Train Given Best Epoch Parameter :' + str(best_epoch[0]))
                for i in range(best_epoch[0]):
                    print("Epoch: %d" % (i + 1))
                    if config.ptb == False:
                        _, _, _, _, _, _, _, _, _, _ = \
                            run_epoch(session, mTrain,
                                      words_ptb, pos_ptb, chunk_ptb,
                                      num_pos_tags, num_chunk_tags, vocab_size, num_steps,
                                      verbose=True, model_type="LM")

                    _, posp_c, chunkp_c, _, _, _, _, _, _, _ = \
                        run_epoch(session, mTrain,
                                  words_c, pos_c, chunk_c,
                                  num_pos_tags, num_chunk_tags, vocab_size,
                                  verbose=True, model_type=model_type)

            else:
                print('Train Given Best Epoch Parameter :' + str(best_epoch[0]))
                for i in range(best_epoch[0]):
                    print("Epoch: %d" % (i + 1))
                    _, posp_c, chunkp_c, _, _, _, _, _, _, _ = \
                        run_epoch_random.run_epoch(session, mTrain,
                                  words_c, words_ptb, pos_c, pos_ptb, chunk_c, chunk_ptb,
                                  num_pos_tags, num_chunk_tags, vocab_size, num_steps,
                                  verbose=True, model_type=model_type)


            print('Getting Testing Predictions')
            _, posp_test, chunkp_test, _, _, _, _, _, _, _ = \
                run_epoch(session, mTest,
                          words_test, pos_test, chunk_test,
                          num_pos_tags, num_chunk_tags, vocab_size, num_steps,
                          verbose=True, valid=True, model_type=model_type)


            print('Writing Predictions')
            # prediction reshaping
            posp_c = reader._res_to_list(posp_c, config.batch_size,
                                         pos_to_id, len(words_c), combined_lengths, to_str=True)
            posp_test = reader._res_to_list(posp_test, config.batch_size,
                                            pos_to_id, len(words_test), test_lengths,to_str=True)
            chunkp_c = reader._res_to_list(chunkp_c, config.batch_size,
                                           chunk_to_id, len(words_c), combined_lengths,to_str=True)
            chunkp_test = reader._res_to_list(chunkp_test, config.batch_size,
                                              chunk_to_id, len(words_test), test_lengths, to_str=True)

            # save pickle - save_path + '/saved_variables.pkl'
            print('saving checkpoint')
            saveload.save(save_path + '/fin_model.ckpt', session)

            train_custom = reader.read_tokens(raw_data_path + '/train.txt', -1)
            valid_custom = reader.read_tokens(raw_data_path + '/validation.txt',-1)
            combined = reader.read_tokens(raw_data_path + '/train_val_combined.txt', -1)
            test_data = reader.read_tokens(raw_data_path + '/test.txt',-1)

            print('loaded text')

            if test==False:
                chunk_pred_train = np.concatenate((np.transpose(train_custom), np.char.upper(chunkp_t[:len(train_custom[0])]).reshape(-1,1)), axis=1)
                chunk_pred_val = np.concatenate((np.transpose(valid_custom), np.char.upper(chunkp_v).reshape(-1,1)), axis=1)
            # chunk_pred_c = np.concatenate((np.transpose(combined), np.char.upper(chunkp_c).reshape(-1,1)), axis=1)
            chunk_pred_test = np.concatenate((np.transpose(test_data), np.char.upper(chunkp_test).reshape(-1,1)), axis=1)
            if test==False:
                pos_pred_train = np.concatenate((np.transpose(train_custom), np.char.upper(posp_t[:len(train_custom[0])]).reshape(-1,1)), axis=1)
                pos_pred_val = np.concatenate((np.transpose(valid_custom), np.char.upper(posp_v).reshape(-1,1)), axis=1)
            # pos_pred_c = np.concatenate((np.transpose(combined), np.char.upper(posp_c).reshape(-1,1)), axis=1)
            pos_pred_test = np.concatenate((np.transpose(test_data), np.char.upper(posp_test).reshape(-1,1)), axis=1)

            print('finished concatenating, about to start saving')

            if test == False:
                np.savetxt(save_path + '/predictions/chunk_pred_train.txt',
                           chunk_pred_train, fmt='%s')
                print('writing to ' + save_path + '/predictions/chunk_pred_train.txt')
                np.savetxt(save_path + '/predictions/chunk_pred_val.txt',
                           chunk_pred_val, fmt='%s')
                print('writing to ' + save_path + '/predictions/chunk_pred_val.txt')
            np.savetxt(save_path + '/predictions/chunk_pred_combined.txt',
                       chunk_pred_c, fmt='%s')
            print('writing to ' + save_path + '/predictions/chunk_pred_combined.txt')
            np.savetxt(save_path + '/predictions/chunk_pred_test.txt',
                       chunk_pred_test, fmt='%s')
            print('writing to ' + save_path + '/predictions/chunk_pred_test.txt')
            if test == False:
                np.savetxt(save_path + '/predictions/pos_pred_train.txt',
                           pos_pred_train, fmt='%s')
                print('writing to ' + save_path + '/predictions/pos_pred_train.txt')
                np.savetxt(save_path + '/predictions/pos_pred_val.txt',
                           pos_pred_val, fmt='%s')
                print('writing to ' + save_path + '/predictions/pos_pred_val.txt')
            np.savetxt(save_path + '/predictions/pos_pred_combined.txt',
                       pos_pred_c, fmt='%s')
            np.savetxt(save_path + '/predictions/pos_pred_test.txt',
                       pos_pred_test, fmt='%s')

        else:
            print('Best Validation Loss ' + str(best_epoch[1]))
            print('Best Validation Epoch ' + str(best_epoch[0]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_type")
    parser.add_argument("--dataset_path")
    parser.add_argument("--ptb_path")
    parser.add_argument("--glove_path")
    parser.add_argument("--save_path")
    parser.add_argument("--num_steps")
    parser.add_argument("--encoder_size")
    parser.add_argument("--pos_decoder_size")
    parser.add_argument("--chunk_decoder_size")
    parser.add_argument("--dropout")
    parser.add_argument("--batch_size")
    parser.add_argument("--pos_embedding_size")
    parser.add_argument("--num_shared_layers")
    parser.add_argument("--num_private_layers")
    parser.add_argument("--chunk_embedding_size")
    parser.add_argument("--lm_decoder_size")
    parser.add_argument("--bidirectional")
    parser.add_argument("--lstm")
    parser.add_argument("--mix_percent")
    parser.add_argument("--write_to_file")
    parser.add_argument("--embedding")
    parser.add_argument("--max_epoch")
    parser.add_argument("--test")
    args = parser.parse_args()
    if (str(args.model_type) != "POS") and (str(args.model_type) != "CHUNK"):
        args.model_type = 'JOINT'
    print('Model Selected : ' + str(args.model_type))
    main(str(args.model_type),str(args.dataset_path), \
         str(args.ptb_path),str(args.save_path), \
         int(args.num_steps), int(args.encoder_size), \
         int(args.pos_decoder_size), int(args.chunk_decoder_size), \
         float(args.dropout), int(args.batch_size), \
         int(args.pos_embedding_size), int(args.num_shared_layers), int(args.num_private_layers), \
         int(args.chunk_embedding_size), int(args.lm_decoder_size), \
         int(args.bidirectional), int(args.lstm), int(args.write_to_file), float(args.mix_percent), \
         str(args.glove_path), int(args.max_epoch),int(args.embedding),int(args.test))
