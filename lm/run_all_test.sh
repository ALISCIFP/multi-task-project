echo 'Run Model'
#LD_LIBRARY_PATH="$HOME/utils/libc6_2.17/lib/x86_64-linux-gnu/:$HOME/utils/libc6_2.17/usr/lib64/" \
# $HOME/utils/libc6_2.17/lib/x86_64-linux-gnu/ld-2.17.so `which python` \
python3 run_model.py --model_type "JOINT" \
                     --dataset_path "../../data/conll_toy" \
                     --ptb_path "../../data/conll_toy" \
                     --save_path "../../data/outputs/test" \
                     --glove_path '../../data/glove.6B/glove.6B.300d.txt' \
                     --num_steps 20 \
                     --encoder_size 200 \
                     --pos_decoder_size 200 \
                     --chunk_decoder_size 200 \
                     --dropout 0.5 \
                     --batch_size 10 \
                     --pos_embedding_size 400 \
                     --num_shared_layers 1 \
                     --num_private_layers 1 \
                     --chunk_embedding_size 400 \
                     --lm_decoder_size  200 \
                     --bidirectional 1 \
                     --lstm 1 \
                     --mix_percent 0.7 \
                     --write_to_file 0 \
                     --embedding 1 \
                     --max_epoch 10 \
		                 --test 0 \
		                 --projection_size 100 \
                     --num_gold 15 \
                     --reg_weight 0.01 \
	                   --word_embedding_size 300 \
		                 --embedding_trainable 0 \
                     --adam 1 \
                     --fraction_of_training_data 1 \
                     --connections 0
