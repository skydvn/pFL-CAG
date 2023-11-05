import torch
import time
from flcore.clients.clientCAGrad import clientCAGrad
from flcore.servers.serverbase import Server
from threading import Thread
import numpy as np
import yaml
import copy

class FedCAGrad(Server):
    def __init__(self, args, times):
        super().__init__(args, times)

        # select slow clients
        self.set_slow_clients()
        self.set_clients(clientCAGrad)

        print(f"\nJoin ratio / total clients: {self.join_ratio} / {self.num_clients}")
        print("Finished creating server and clients.")
        self.Budget = []
        self.update_grads = None
        self.cagrad_c = 0.5

    def train(self):
        for i in range(self.global_rounds+1):
            s_t = time.time()
            self.selected_clients = self.select_clients()
            self.send_models()

            if i % self.eval_gap == 0:
                print(f"\n-------------Round number: {i}-------------")
                print("\nEvaluate global model")
                self.evaluate()

            for client in self.selected_clients:
                client.train()

            self.receive_models()
            self.receive_grads()
            # self.update_grads = gradient_update(self.grads)

            grad_dims = []
            for mm in self.global_model.shared_modules():
                for param in mm.parameters():
                    grad_dims.append(param.data.numel())
            grads = torch.Tensor(sum(grad_dims), self.num_clients).cuda()

            for k in range(self.num_clients):
                grad2vec(self.global_model, grads, grad_dims, k)
                self.global_model.zero_grad_shared_modules()
            g = self.cagrad(grads, self.num_clients)



            if self.dlg_eval and i % self.dlg_gap == 0:
                self.call_dlg(i)
            # self.aggregate_parameters()

            self.Budget.append(time.time() - s_t)
            print('-'*25, 'time cost', '-'*25, self.Budget[-1])

            if self.auto_break and self.check_done(acc_lss=[self.rs_test_acc], top_cnt=self.top_cnt):
                break

        print("\nBest accuracy.")
        # self.print_(max(self.rs_test_acc), max(
        #     self.rs_train_acc), min(self.rs_train_loss))
        print(max(self.rs_test_acc))
        print("\nAverage time cost per round.")
        print(sum(self.Budget[1:])/len(self.Budget[1:]))

        self.save_results()
        self.save_global_model()

        if self.num_new_clients > 0:
            self.eval_new_clients = True
            self.set_new_clients(clientCAGrad)
            print(f"\n-------------Fine tuning round-------------")
            print("\nEvaluate new clients")
            self.evaluate()

    def cagrad(self, grad_vec, num_tasks):
        """
        grad_vec: [num_tasks, dim]
        """
        grads = grad_vec

        GG = grads.mm(grads.t()).cpu()
        scale = (torch.diag(GG)+1e-4).sqrt().mean()
        GG = GG / scale.pow(2)
        Gg = GG.mean(1, keepdims=True)
        gg = Gg.mean(0, keepdims=True)

        # gg is scalar

        w = torch.zeros(num_tasks, 1, requires_grad=True)                                          # w

        if num_tasks == 50:
            w_opt = torch.optim.SGD([w], lr=50, momentum=0.5)                               #
        else:
            w_opt = torch.optim.SGD([w], lr=25, momentum=0.5)

        c = (gg+1e-4).sqrt() * self.cagrad_c

        w_best = None
        obj_best = np.inf
        for i in range(21):
            w_opt.zero_grad()
            ww = torch.softmax(w, 0)
            obj = ww.t().mm(Gg) + c * (ww.t().mm(GG).mm(ww) + 1e-4).sqrt()
            if obj.item() < obj_best:
                obj_best = obj.item()
                w_best = w.clone()
            if i < 20:
                obj.backward()
                w_opt.step()

        ww = torch.softmax(w_best, 0)
        gw_norm = (ww.t().mm(GG).mm(ww)+1e-4).sqrt()

        lmbda = c.view(-1) / (gw_norm+1e-4)
        g = ((1/num_tasks + ww * lmbda).view(
            -1, 1).to(grads.device) * grads).sum(0) / (1 + self.cagrad_c**2)
        return g


def grad2vec(m, grads, grad_dims, task):
    # store the gradients
    grads[:, task].fill_(0.0)
    cnt = 0
    for mm in m.shared_modules():
        for p in mm.parameters():
            grad = p.grad
            if grad is not None:
                grad_cur = grad.data.detach().clone()
                beg = 0 if cnt == 0 else sum(grad_dims[:cnt])
                en = sum(grad_dims[:cnt + 1])
                grads[beg:en, task].copy_(grad_cur.data.view(-1))
            cnt += 1


# def gradient_update(grads):
#     grad_update = []
#
#     def flatten_params(parameters):
#         """
#         flattens all parameters into a single column vector. Returns the dictionary to recover them
#         param: parameters: a generator or list of all the parameters
#         return: a dictionary: {"params": [#params, 1],
#         "indices": [(start index, end index) for each param] **Note end index in uninclusive**
#         """
#         l = [torch.flatten(p) for p in parameters]
#         indices = []
#         s = 0
#         for p in l:
#             size = p.shape[0]
#             indices.append((s, s + size))
#             s += size
#         flat = torch.cat(l).view(-1, 1)
#         # return {"params": flat, "indices": indices}
#         return flat.t()
#
#     for grad_model in grads:
#         grad_update.append(flatten_params(grad_model.parameters()))
#         grad_update = torch.vstack(grad_update)
#     return grad_update

























