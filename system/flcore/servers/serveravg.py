import time
from flcore.clients.clientavg import clientAVG
from flcore.servers.serverbase import Server
from threading import Thread
import numpy
import copy
# import yaml
import statistics


class FedAvg(Server):
    def __init__(self, args, times):
        super().__init__(args, times)

        # select slow clients
        self.set_slow_clients()
        self.set_clients(clientAVG)
        self.set_new_clients(clientAVG)
        self.args = args

        print(f"\nJoin ratio / total clients: {self.join_ratio} / {self.num_clients}")
        print("Finished creating server and clients.")

        # self.load_model()
        self.Budget = []
        self.device = args.device
        model_origin = copy.deepcopy(args.model)


    def train(self):
        for i in range(self.global_rounds+1):
            s_t = time.time()
            self.selected_clients = self.select_clients()
            self.send_models()
            self.set_new_client_domain()
            # print(f"global_model parameters")
            # for param in self.global_model.conv1.parameters():
            #     print(param)

            # print(f"global_model parameters grad")
            # for param in self.global_model.conv1.parameters():
            #     print(param)

            if i % self.eval_gap == 0:
                print(f"\n-------------Round number: {i}-------------")
                print("\nEvaluate global model")
                self.evaluate()
                if self.args.domain_training:
                    self.domain_evaluate()

            for client in self.selected_clients:
                client.train()

            self.receive_models()
            self.receive_grads()
            model_origin = copy.deepcopy(self.global_model)
            # if self.dlg_eval and i % self.dlg_gap == 0:
            #     self.call_dlg(i)
            # self.model_aggregate_new()
            self.aggregate_parameters()
            angle = [self.cos_sim(model_origin, self.global_model, models) for models in self.grads]
            # print(angle)
            self.angle_ug = statistics.mean(angle)

            user_cnt = 0
            neg_cnt = 0
            total_diff = 0
            total_neg_diff = 0
            for i_domain, i_model in enumerate(self.grads):
                for j_domain, j_model in enumerate(self.grads):
                    if j_domain > i_domain:
                        user_cnt += 1
                        diff = self.cos_sim(model_origin, i_model, j_model)
                        # print(diff)
                        if diff < 0:
                            total_neg_diff += diff
                            neg_cnt += 1

                        total_diff += diff
            self.angle_uv = total_diff / user_cnt
            self.angle_neg_uv = total_neg_diff / neg_cnt
            self.angle_neg_ratio = neg_cnt / ((self.args.num_clients * self.args.join_ratio)
                                              *(self.args.num_clients * self.args.join_ratio - 1)/2)
            print(f"user: {user_cnt} /neg:{neg_cnt}")

            # print(f"model_update")
            # for param in self.global_model.conv1.parameters():
            #     print(param)

            # for param in self.model_subtraction.parameters():
            #     print(f"number param: {param.numel()} and param: {param.data}")

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

        # if self.num_new_clients > 0:
        #     self.eval_new_clients = True
        #     self.set_new_clients(clientAVG)
        #     print(f"\n-------------Fine tuning round-------------")
        #     print("\nEvaluate new clients")
        #     self.domain_evaluate()
