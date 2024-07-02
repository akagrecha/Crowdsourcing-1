import pytest
import numpy as np

from worker_aggregation import EMSymmetricBinary

@pytest.fixture
def synthetic_data():
    def _synthetic_data(seed: int, num_samples: int, num_models: int):
        rng = np.random.default_rng(seed)
        skill = 0.5 + 0.5*rng.random(num_models)
        ests = np.zeros((num_samples, num_models), dtype=np.int32)
        true_labels = np.zeros(num_samples, dtype=np.int32)
        for i in range(num_samples):
            true_label = rng.integers(0, 2)
            true_labels[i] = true_label
            for j in range(num_models):
                if true_label == 1:
                    ests[i, j] = rng.choice([0, 1], p=[1-skill[j], skill[j]])
                else:
                    ests[i, j] = rng.choice([0, 1], p=[skill[j], 1-skill[j]])
        return ests, true_labels, skill
    return _synthetic_data

class TestEMSymmetricBinary:
    def test_single_sample(self,):
        skill_init = np.array([0.6, 0.7, 0.8])
        em_model = EMSymmetricBinary(seed=42, num_models=3, skill_init=skill_init)
        ests = np.array([[0, 1, 1]])
        exp_prob_1 = 0.4*0.7*0.8/(0.4*0.7*0.8 + 0.6*0.3*0.2)
        prob_1 = em_model.e_step(ests)
        assert np.isclose(prob_1, exp_prob_1)
        print("E-step test passed")

        ## M-step test
        exp_skill = np.array([1-prob_1[0], prob_1[0], prob_1[0]])
        skill = em_model.m_step(ests, prob_1)
        # print(exp_skill)
        # print(skill)
        assert np.allclose(skill, exp_skill)
        print("M-step test passed")
    
    def test_synthetic_data(self, synthetic_data):
        num_samples = 10000
        num_models = 5
        ests, _, skill = synthetic_data(seed=42, num_samples=num_samples, num_models=num_models)
        em_model = EMSymmetricBinary(seed=42, num_models=num_models)
        em_model.fit(ests)
        logit_skill = np.log(skill) - np.log(1-skill)
        logit_em_skill = np.log(em_model.skill) - np.log(1-em_model.skill)
        assert np.allclose(logit_skill, logit_em_skill, atol=1e-1)
        print("Synthetic data test passed")