# Project:
#   VQA
# Description:
#   File to implement visual datasets
# Author: 
#   Binhui Ge

import os
import h5py
import torch
from os.path import join as jp
from PIL import Image
import torchvision.transforms as transforms
from torch.utils.data import Dataset


def read_image_names(path_txt):
    with open(path_txt, 'r') as f:
        lines = f.readlines()
    map_index_name = [elem[:-1] for elem in lines] # remove char '\n'
    map_name_index = {elem[:-1]:i for i,elem in enumerate(lines)}
    return map_index_name, map_name_index

class FeaturesDataset(Dataset):
    def __init__(self, subset, config):
        self.subset = subset 
        self.config = config
        self.path_extracted = jp(config['path_img'], 'extracted')
        self.path_features = jp(self.path_extracted, subset + 'set.hdf5')
        self.data = h5py.File(self.path_features)['features'] # ! important, save features dataset as 'features'
        self.map_index_name, self.map_name_index = read_image_names(jp(self.path_extracted, subset + 'set.txt'))

    def get_by_name(self, image_name):
        return self.__getitem__(self.map_name_index[image_name])

    def __getitem__(self, index):
        sample = {} 
        sample['name'] = self.map_index_name[index]
        sample['visual'] = torch.Tensor(self.data[index])
        return sample

    def __len__(self):
        return self.data.shape[0]


class ImagesDataset(Dataset):

    def __init__(self, subset, config, transform=None):
        self.subset = subset
        self.path_img = config['path_img']#将路径组合（jp为os.path.join）
        self.transform = transform
        self.images =[i+'/source.jpg' for i in os.listdir(self.path_img)] # list all images in folder列出文件夹中所有的图片名称
        self.map_name_index = {img:i for i, img in enumerate(self.images)}#enumerate用来遍历一个list对象并且可以得到当前元素的索引。
        #img是图片名称，i是索引（通过名称获得索引）
        #通过索引获得图片名称
        self.map_index_name = self.images

    def get_by_name(self, image_name):
        return self.__getitem__(self.map_name_index[image_name])

    def __getitem__(self, index):
        sample = {} 
        sample['name'] = self.map_index_name[index]
        sample['path'] = jp(self.path_img, sample['name']) # full relative path to image
        sample['visual'] = Image.open(sample['path']).convert('RGB')#表示只读取RGB三个通道的像素信息

        # apply transform(s)
        if self.transform is not None:
            sample['visual'] = self.transform(sample['visual'])

        return sample

    def __len__(self):
        return len(self.images)

class MasksDataset(Dataset):
    def __init__(self, subset, config, mask_name, transform=None):
        self.subset = subset 
        self.mask_name = mask_name
        self.path_masks = jp(config['path_masks'], subset)
        self.transform = transform 
        self.images = os.listdir(jp(self.path_masks, mask_name))
        self.map_name_index = {img:i for i, img in enumerate(self.images)}
        self.map_index_name = self.images

    def get_by_name(self, mask_name):
        return self.__getitem__(self.map_name_index[mask_name])

    def __getitem__(self, index):
        sample = {} 
        sample['name'] = self.map_index_name[index]
        sample['path'] = jp(self.path_masks, self.mask_name, sample['name']) # full relative path to image
        sample['mask'] = Image.open(sample['path'])

        # apply transform(s)
        if self.transform is not None:
            sample['mask'] = self.transform(sample['mask'])

        return sample

    def __len__(self):
        return len(self.images)     


def default_transform(size):
    """Define basic (standard) transform for input images, as required by image processor

    Parameters
    ----------
    size : int or tuple
        new size for the images

    Returns
    -------
    torchvision transform
        composed transform for files
    """
    transform = transforms.Compose([
        transforms.Resize(size),#将给定的图片更改为size大小
        transforms.CenterCrop(size),#在图片的中心位置进行裁剪
        transforms.ToTensor(),#把灰度范围从0-255变换为0-1之间
        transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                             std=[0.229, 0.224, 0.225])
        #由于是三个通道，将每个通道的灰度的mean和std改为上图所示。
        #image（new）=(image-mean)/std;
    ])#通过transforms.Compose将多个transforms操作融合一起
    return transform

def default_inverse_transform():
    # undoes basic ImageNet normalization
    transform = transforms.Compose([ transforms.Normalize(mean = [ 0., 0., 0. ],
                                                        std = [ 1/0.229, 1/0.224, 1/0.225 ]),
                                    transforms.Normalize(mean = [ -0.485, -0.456, -0.406 ],
                                                        std = [ 1., 1., 1. ]),
                                ])
    return transform
                    


def mask_transform(size):
    transform = transforms.Compose([
        transforms.Resize(size),
        transforms.CenterCrop(size),
        transforms.ToTensor()
    ])
    return transform

def get_visual_dataset(subset, config, transform=None):
    """Get visual dataset either from images or from extracted features

    Parameters
    ----------
    split : str
        split name (train, val, test, trainval)
    options_visual : dict
        visual options as determined in yaml file
    transform : torchvision transform, optional
        transform to be applied to images, by default None

    Returns
    -------
    images dataset
        images dataset with images or feature maps (depending on options_visual['mode'])
    """
    if config['pre_extracted_visual_feat']: # if features were already extracted
        visual_dataset = FeaturesDataset(subset, config) # load pre-extracted features导入预先提取的图像特征
    else: # if features were not previously extracted
        if transform is None:
            transform = default_transform(config['size'])
        visual_dataset = ImagesDataset(subset, config, transform) # create images dataset
    return visual_dataset


def get_mask_dataset(subset, config, mask_name, transform=None):

    if transform is None:
        transform = mask_transform(config['size'])
    mask_dataset = MasksDataset(subset, config, mask_name, transform)
    return mask_dataset