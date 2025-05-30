'''
No@
Jan 31st, 2024
'''

import os
from config import Arguments_test
from lib.unet.unet_model import UNet
from lib.custom_networks import Trans_no_patch_embed, IRGS_Trans
from icecream import ic
import wandb
from utils.dataloader import RadarSAT2_Dataset
import numpy as np
from skimage.morphology import disk, binary_dilation

import matplotlib.pyplot as plt
from PIL import Image
from sklearn.metrics import accuracy_score
from utils.utils import Metrics, get_contours, hex_to_rgb
from mycolorpy import colorlist as mcp
import csv

colors = mcp.gen_color(cmap="jet", n=256)
colors_rgb = np.asarray([hex_to_rgb(i) for i in colors])



if __name__ == '__main__':

    args = Arguments_test()

    # args.mode = 'multi_stage'
    # args.loss_term = 'cnn'
    # args.stage = 'cnn'
    # args.test_path = ['20100524']
    # args.model_name = 'model_3'

    if args.stage == 'cnn' and args.mode == 'end_to_end' and args.loss_term == 'transformer':
        raise AssertionError("Model trained using ONLY TRANSFORMER LOSS does not work for the cnn prediction")

#%% ============== MODEL NAME =============== #
    cnn = UNet(args.in_chans, args.n_classes)
    transformer = Trans_no_patch_embed(n_in_feat=32, num_classes=args.n_classes, 
                                        embed_dim=args.embed_dim, depth=args.trans_depth, 
                                        num_heads=args.num_heads)
    # ================ MERGE CNN - TRANSFORMER
    model = IRGS_Trans(cnn, transformer, args.max_length, 
                                  args.mix_images, args.random_tokens)

#%% ============== DIRECTORY =============== #
    if args.mode == 'end_to_end':
        if args.loss_term == 'transformer':
            args.save_path =  os.path.join(args.save_path, args.Dataset_name, 
                                           model.net_name + '_' + args.token_option, 
                                           'end_to_end', 'Loss_transformer', args.model_name)
        else:
            args.save_path =  os.path.join(args.save_path, args.Dataset_name, 
                                           model.net_name + '_' + args.token_option, 
                                           'end_to_end', 'Loss_end_to_end', args.model_name)
        project_name = '-'.join([model.net_name, args.token_option, args.mode, 'Loss_' + args.loss_term])

    elif args.mode == 'multi_stage':
        if args.loss_term == 'end_to_end':
            args.save_path =  os.path.join(args.save_path, args.Dataset_name, 
                                           model.net_name + '_' + args.token_option, 
                                           'multi_stage', 'Loss_end_to_end', args.model_name)
            project_name = '-'.join([model.net_name, args.token_option, args.mode, 'Loss_' + args.loss_term])

        elif args.loss_term == 'transformer':
            args.save_path =  os.path.join(args.save_path, args.Dataset_name, 
                                           model.net_name + '_' + args.token_option, 
                                           'multi_stage', 'Loss_transformer', args.model_name)
            project_name = '-'.join([model.net_name, args.token_option, args.mode, 'Loss_' + args.loss_term])
            args.stage = 'transformer'

        elif args.loss_term == 'cnn':
            args.save_path =  os.path.join(args.save_path, args.Dataset_name, cnn.net_name, args.model_name)
            args.stage = 'cnn'
            project_name = cnn.net_name

    # ic(args.save_path)

#%% ============== TESTING =============== #
    output_folder = os.path.join(args.save_path, args.test_path[0])
    if args.loss_term == 'end_to_end':
        output_folder = os.path.join(output_folder, args.stage)

    # =========== LOAD DATA AND PRED MAPS
    test_data =  RadarSAT2_Dataset(args, name = args.test_path[0], set_="test")
    landmask_idx = test_data.background==0
    probs_map = np.load(output_folder + '/probabilities_predict_%s.npy'%(args.stage))
    # =========== SOFT-LABELS
    colored_softlbl = np.uint8(colors_rgb[np.uint8(255*probs_map[1])])
    colored_softlbl[landmask_idx] = [255, 255, 255]
    Image.fromarray(colored_softlbl).save(output_folder + '/soft_lbl_%s.png'%(args.stage))

    pred_map = np.argmax(probs_map, 0)
    if len(np.unique(test_data.gts[landmask_idx==0])) > 1:      # single class scenes don't show edges

        output_folder = os.path.join(output_folder, 'buffers')
        os.makedirs(output_folder, exist_ok=True)

        wandb.init(project=project_name, name=args.stage, group=args.model_name, job_type='edge_buffer')

        # =========== CREATE BUFFERS
        contours = get_contours(test_data.gts)
        contour_mask = np.zeros_like(test_data.gts)
        contour_mask[contours[:,0], contours[:,1]] = 1

        for width in range(0, 20):

            edge_buffer = np.uint8(binary_dilation(contour_mask, disk(width)))
            edge_buffer[landmask_idx] = 0
            # Image.fromarray(np.uint8(edge_buffer*255)).save(output_folder + '/edge_buffer_%d.png'%(width))

            # =========== METRICS
            y_true = test_data.gts[edge_buffer==1]
            y_pred = pred_map[edge_buffer==1]
            acc, IoU = Metrics(y_true, y_pred, None, None)

            wandb.summary['buffer_{:02d}_OA'.format(width+1)] = acc
            wandb.summary['buffer_{:02d}_IoU0'.format(width+1)] = IoU[0]
            wandb.summary['buffer_{:02d}_IoU1'.format(width+1)] = IoU[1]
            # with open(output_folder + '/metrics_buffer.csv', 'a', encoding='UTF8', newline='') as f:
            #     writer = csv.writer(f)
            #     writer.writerow(['buffer_{:02d}_OA'.format(width+1), acc])


#python buffer_metrics.py --mode multi_stage --loss_term cnn --stage cnn --test_path 20100605 --model_name model_4
