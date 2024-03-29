#! /usr/bin/python3
from glob import glob
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
import numpy as np
import os
import cv2
import pykitti
from itertools import compress
import pickle

height = 375
width = 1242

path = 'data/output/kitti/test/180426/3'

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import skimage.transform

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

trainlen = min(1000, 443)
epoch = 10
batchsize = min(4, trainlen)
mode = 'train'

projlist = np.load(os.path.join(path,'proj_cloud_point.npy'))[:trainlen]
dispn = np.load(os.path.join(path,'disp.npy'))[:trainlen].reshape(trainlen, 1, 256, 512)

print(dispn.shape)
print(projlist.shape)

class simplecnn(nn.modules.Module):

    def __init__(self):
        super(simplecnn, self).__init__()
        self.conv = nn.Sequential(
        	nn.Conv2d(1, 64, kernel_size=3, stride=1, padding=1),
        	nn.ReLU()
        	)
        self.fc = nn.Sequential(
        	nn.Linear(64, 64),
        	nn.Sigmoid(),
        	nn.Linear(64, 1),
        	nn.ReLU()
        	)

    def forward(self, x):
    	x = self.conv(x)
    	x = x.permute(0, 2, 3, 1)
    	x = self.fc(x)
    	return x

torch.manual_seed(598)
disp = torch.tensor(dispn, dtype=torch.float32).to(device)
projlist = torch.tensor(projlist.reshape((trainlen, 256, 512, 1)), dtype=torch.float32).to(device)
net = simplecnn().to(device)
optimizer = optim.Adam(net.parameters(), lr = 0.01)
loss = []

if mode == 'train':
	for epochi in range(epoch):

		running_loss = 0.0
		batchnum = disp.shape[0] // batchsize

		for i in range(batchnum):

			batch_idx = np.random.choice(trainlen, batchsize, replace=False)
			disp_batch = disp[batch_idx, :].to(device)
			projlist_batch = projlist[batch_idx, :].to(device)

			optimizer.zero_grad()

			predrect_batch = net(disp_batch)
			diff = predrect_batch-projlist_batch

			running_loss = torch.mean(torch.abs(diff[diff == diff])).to(device)
			loss.append(running_loss)

			running_loss.backward()
			optimizer.step()

			if i % 10 == 0:
				print('[epoch %d, iter %3d] \n     - loss: %.8f' %
	                      (epochi + 1, i + 1, running_loss / batchsize))

	np.save(os.path.join(path, 'loss'), loss)
	for i in range(disp.shape[0]):
		disp_to_depth = net(disp[i].resize(1,1,256, 512)).reshape(256, 512)
		dpt = disp_to_depth.to('cpu').detach().numpy()
		k = np.max(np.abs(dpt))
		dpt = dpt / k
		dpt = cv2.resize(dpt, (1242, 375))
		dpt = dpt * k
		if i == 0:
			'''
			f = plt.figure()
			p = plt.imshow(dpt)
			f.colorbar(p, orientation='vertical')
			plt.show()
			plt.close()
			'''
		np.save(os.path.join(path, 'depth'+str(i)), dpt)

else:
	a = np.load(os.path.join(path, 'depth0.npy'))
	dpt = projlist[0].to('cpu').numpy().reshape((256, 512))
	
	fig1 = plt.figure(1, figsize=(8, 16))
	ax1 = fig1.add_subplot(1, 1, 1)
	p = ax1.imshow(a, cmap='jet')
	plt.xlim([0, 1242])
	plt.ylim([0, 375])
	fig1.colorbar(p, orientation='vertical')
	ax1.axis('scaled')
	plt.show()
	plt.close()

	fig2 = plt.figure(2, figsize=(8, 16))
	ax2 = fig2.add_subplot(1, 1, 1)
	pp = ax2.imshow(dpt, cmap='jet')
	plt.xlim([0, 512])
	plt.ylim([0, 256])
	fig2.colorbar(pp, orientation='vertical')
	ax2.axis('scaled')
	plt.show()
	plt.close()

	fig3 = plt.figure(3, figsize=(8, 16))
	ax3 = fig3.add_subplot(1, 1, 1)
	a = dispn[0,:,:,0].reshape(256,512)
	ppp = ax3.imshow(a, cmap='jet')
	plt.xlim([0, 512])
	plt.ylim([0, 256])
	fig3.colorbar(pp, orientation='vertical')
	ax3.axis('scaled')
	plt.show()
	plt.close()