# Hamiltonian Neural Networks | 2019
# Sam Greydanus, Misko Dzamba, Jason Yosinski

import torch, argparse, os
import numpy as np

import os, sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from nn_models import MLP
from hnn import HNN, HNNBaseline
from data import get_dataset
from utils import L2_loss

def get_args():
    parser = argparse.ArgumentParser(description=None)
    parser.add_argument('--input_dim', default=2, type=int, help='dimensionality of input tensor')
    parser.add_argument('--hidden_dim', default=200, type=int, help='hidden dimension of mlp')
    parser.add_argument('--learn_rate', default=1e-3, type=float, help='learning rate')
    parser.add_argument('--input_noise', default=0.0, type=int, help='std of noise added to HNN inputs')
    parser.add_argument('--nonlinearity', default='tanh', type=str, help='neural net nonlinearity')
    parser.add_argument('--total_steps', default=2000, type=int, help='number of gradient steps')
    parser.add_argument('--print_every', default=200, type=int, help='number of gradient steps between prints')
    parser.add_argument('--name', default='real', type=str, help='either "real" or "sim" data')
    parser.add_argument('--baseline', dest='baseline', action='store_true', help='run baseline or experiment?')
    parser.add_argument('--seed', default=0, type=int, help='random seed')
    parser.add_argument('--save_dir', default='.', type=str, help='name of dataset')
    parser.set_defaults(feature=True)
    return parser.parse_args()

def train(args):
  # set random seed
  torch.manual_seed(args.seed)
  np.random.seed(args.seed)

  # init model and optimizer
  print("Training baseline model:" if args.baseline else "Training HNN model:")
  if args.baseline:
    nn_model = MLP(args.input_dim, args.hidden_dim, args.input_dim, nonlinearity=args.nonlinearity)
    model = HNNBaseline(args.input_dim, baseline_model=nn_model)
  else:
    nn_model = MLP(args.input_dim, args.hidden_dim, 2, nonlinearity=args.nonlinearity)
    model = HNN(args.input_dim, differentiable_model=nn_model)

  optim = torch.optim.Adam(model.parameters(), args.learn_rate)

  # arrange data
  data, names = get_dataset(args.name, args.save_dir)
  np_x, np_t = data[:,2:4], data[:,1:2]
  delta_x = (np_x[1:] - np_x[:-1]) / (np_t[1:] - np_t[:-1])
  np_x= np_x[:-1]
  
  x = torch.tensor( np_x, requires_grad=True, dtype=torch.float32)
  dxdt = torch.Tensor(delta_x)

  # vanilla train loop
  stats = {'train_loss': []}
  for step in range(args.total_steps+1):

    noise = args.input_noise * torch.randn(*x.shape)
    dxdt_hat = model.time_derivative(x + noise)
    loss = L2_loss(dxdt, dxdt_hat)
    loss.backward() ; optim.step() ; optim.zero_grad()

    stats['train_loss'].append(loss.item())
    if step % args.print_every == 0:
      print("step {}, loss {:.4e}".format(step, loss.item()))

  return model, stats

if __name__ == "__main__":
    args = get_args()
    model, stats = train(args)

    # save
    os.makedirs(args.save_dir) if not os.path.exists(args.save_dir) else None
    label = 'baseline' if args.baseline else 'hnn'
    path = '{}/pendulum-{}-{}.tar'.format(args.save_dir, args.name, label)
    torch.save(model.state_dict(), path)