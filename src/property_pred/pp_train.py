import torch
import pickle
from model import GNN
from dgl.dataloading import GraphDataLoader
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score


def train(args, data):
    path = '../saved/' + args.pretrained_model + '/'
    print('loading hyperparameters of pretrained model from ' + path + 'hparams.pkl')
    with open(path + 'hparams.pkl', 'rb') as f:
        hparams = pickle.load(f)

    print('loading pretrained model from ' + path + 'model.pt')
    mole = GNN(hparams['gnn'], hparams['layer'], hparams['feature_len'], hparams['dim'])
    if torch.cuda.is_available():
        mole.load_state_dict(torch.load(path + 'model.pt'))
        mole = mole.cuda(args.gpu)
    else:
        mole.load_state_dict(torch.load(path + 'model.pt', map_location=torch.device('cpu')))

    dataloader = GraphDataLoader(data, batch_size=args.batch_size, shuffle=True)
    all_features = []
    all_labels = []
    with torch.no_grad():
        mole.eval()
        for graphs, labels in dataloader:
            graph_embeddings = mole(graphs)
            all_features.append(graph_embeddings)
            all_labels.append(labels)
        all_features = torch.cat(all_features, dim=0).cpu().numpy()
        all_labels = torch.cat(all_labels, dim=0).cpu().numpy()

    print('splitting dataset')
    train_features = all_features[: int(0.8 * len(data))]
    train_labels = all_labels[: int(0.8 * len(data))]
    valid_features = all_features[int(0.8 * len(data)): int(0.9 * len(data))]
    valid_labels = all_labels[int(0.8 * len(data)): int(0.9 * len(data))]
    test_features = all_features[int(0.9 * len(data)):]
    test_labels = all_labels[int(0.9 * len(data)):]

    print('training the classification model\n')
    pred_model = LogisticRegression(solver='liblinear')
    pred_model.fit(train_features, train_labels)
    run_classification(pred_model, 'train', train_features, train_labels)
    run_classification(pred_model, 'valid', valid_features, valid_labels)
    run_classification(pred_model, 'test', test_features, test_labels)


def run_classification(model, mode, features, labels):
    train_acc = model.score(features, labels)
    train_auc = roc_auc_score(labels, model.predict_proba(features)[:, 1])
    print('%s acc: %.4f   auc: %.4f' % (mode, train_acc, train_auc))
