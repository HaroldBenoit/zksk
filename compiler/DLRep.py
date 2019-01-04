"""
A module containing multiple classes used to create discrete logarithms proofs.
An example of DL proof would be PK{(x1,x2): y1 = x1 * g1 + x2 * g2} where g1 and g2 are points on a same elliptic curve
over a chosen finite field. 
"""

import random, string
from Subproof import RightSide
from petlib.ec import EcGroup, EcPt
from petlib.bn import Bn
from SigmaProtocol import *
from hashlib import sha256
import binascii
from CompositionProofs import Proof


def randomword(length):
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(length))

def raise_powers(tab_g, response):
    left_arr = [a * b for a, b in zip(response, tab_g)]  # g1^s1, g2^s2...
    leftside = tab_g[0].group.infinite()
    for el in left_arr:
        leftside += el
    return leftside
    
class DLRepProver(Prover):
    """
    The prover in a discrete logarithm proof.
    """
    def __init__(self, generators, secret_names, secret_values, lhs):
        """
        :param generators: a list of elliptic curve points of type petlib.ec.EcPt
        :param secret_names: a list of strings equal to the names of the secrets.
        :param secret_values: the values of the secrets as a dict.
        :param lhs: the left hand side of the equation of the proof of knowledge. If the proof is PK{(x1,x2): y = x1 * g1 + x2 * g2}, lhs is y. 
        """
        self.generators = generators
        self.secret_names = secret_names
        self.secret_values = secret_values
        self.lhs = lhs

        self.set_simulate = False


    def get_secret_values(self):
        return self.secret_values
        
    def get_randomizers(self) -> dict:
        """
        :return: random values to compute the response of the proof of knowledge for each of the secrets. 
        We enforce that if secret are repeated in x1 * g1 + x2 * g2 + ... + xn * gn (that is if xi and xj have the same name) then they will get
        the same random value. 
        """
        output = {}
        for idx, sec in enumerate(self.secret_names): #This overwrites if shared secrets but allows to access the appropriate group order
            key = sec
            to_append = self.generators[idx].group.order().random()
            output.update({key: to_append})
        return output

    def commit(self, randomizers_dict=None):
        """
        :param randomizers_dict: an optional dictionnary of random values. Each random values is assigned to each secret name
        :return: a single commitment (of type petlib.ec.EcPt) for the whole proof
        """

        if self.secret_values == {} : #We check we are not a strawman prover
            raise Exception("Trying to do a legit proof without the secrets. Can only simulate")
        tab_g = self.generators
        G = tab_g[0].group
        self.group_order = G.order()  # Will be useful for all the protocol

        if randomizers_dict == None:  # If we are not provided a randomizer dict from above, we compute it
            secret_to_random_value = self.get_randomizers()
        else:
            secret_to_random_value = randomizers_dict

        self.ks = [secret_to_random_value[sec] for sec in self.secret_names]
        commits = [a * b for a, b in zip(self.ks, tab_g)]

        # We build the commitment doing the product g1^k1 g2^k2...
        sum_ = G.infinite()
        for com in commits:
            sum_ = sum_ + com

        return sum_

    def compute_response(self, challenge):      
        """
        :param challenge: a number of type petlib.bn.Bn
        :return: a list of responses: for each secret we have a response
        for a given secret x and a challenge c and a random value k (associated to x). We have the response equal to k + c * x
        """
        resps = [  # k is a dict with secret names as keys and randomizers as values
            (self.secret_values[self.secret_names[i]].mod_mul(
                challenge, self.group_order)).
            mod_add(
                self.ks[i],
                self.
                group_order,  # If (1) replace by self.ks[self.secret_names[i]]
            ) for i in range(len(self.ks))
        ]
        return resps

    
    def simulate_proof(self, responses_dict = None, challenge = None): #Only function a prover built with empty secret_dict can use
        """
        :param responses_dict: a dictionnary from secret names (strings) to responses (petlib.bn.Bn numbers)
        :param challenge: a petlib.bn.Bn equal to the challenge
        :return: a list of valid commitments for each secret value given responses_dict and a challenge
        """
        #Set the recompute_commitment
        self.recompute_commitment = DLRepProof.recompute_commitment   
        if responses_dict is None:
            responses_dict = self.get_randomizers() 
        if challenge is None:
            challenge = chal_128bits()
        
        response = [responses_dict[m] for m in self.secret_names] #random responses, the same for shared secrets
        commitment = self.recompute_commitment(self, challenge, response)

        return commitment, challenge, response

class DLRepVerifier(Verifier):
    def __init__(self, generators, secret_names, lhs) :
        self.generators = generators
        self.secret_names = secret_names
        self.lhs = lhs
        self.recompute_commitment = DLRepProof.recompute_commitment  



class DLRepProof(Proof):
    """The class is used to model a discrete logarithm proof
    for the sake of having an example say we want to create the proof PK{(x1, x2): y = x1 * g1 + x2 * g2}
    """

    def __init__(self, lhs, rightSide):
        """
        :param rightSide: an instance of the 'RightSide' class. For the previous example 'rightSide' would be: Secret("x1") * g1 + Secret("x2") * g2. Here gi-s are instances of petlib.ec.EcPt
        :param lhs: an instance of petlib.ec.EcPt. The prover has to prove that he knows the secrets xi-s such that x1 * g1 + x2 * g2 + ... + xn * gn = lhs
        """
        if isinstance(rightSide, RightSide):
            self.initialize(rightSide.pts, [secret.name for secret in rightSide.secrets], lhs)
        else:
            raise Exception("undefined behaviour for this input")



    #len of secretDict and generators param of __init__ must match exactly
    def initialize(self, generators, secret_names, lhs):
        """
        this method exists for historical reasons. It is used in __init__ of this class.
        :param generators: a list of petlib.ec.EcPt
        :secret_names: a list of strings equal to the names of the secrets
        """
        if not isinstance(generators, list):  # we have a single generator
            raise Exception("generators must be a list of generators values")

        if isinstance(generators, list) and len(generators) == 0:
            raise Exception(
                "A list of generators must be of length at least one.")

        if not isinstance(secret_names, list):
            raise Exception("secret_names must be a list of secrets names")

        if len(secret_names) != len(generators):
            raise Exception(
                "secret_names and generators must be of the same length")

        # Check all the generators live in the same group
        test_group = generators[0].group
        for g in generators:
            if g.group != test_group:
                raise Exception(
                    "All generators should come from the same group", g.group)

        self.generators = generators
        self.secret_names = secret_names
        self.lhs = lhs
        self.simulate = False


    def get_prover(self, secrets_dict):
        """
        :param secrets_dict: a dictionnary mapping secret names to petlib.bn.Bn numbers
        :return: an instance of DLRepProver
        """
        if self.simulate == True or secrets_dict == {}:
            print('Can only simulate')
            return get_verifier()
        if len(set(self.secret_names)) != len(secrets_dict):
            raise Exception("We expect as many secrets as different aliases")

        if not isinstance(secrets_dict, dict):
            raise Exception("secrets_dict should be a dictionary")

        # Check that the secret names and the keys of the secret values actually match. Could be simplified since it only matters that all names are in dict
        secret_names_set = set(self.secret_names)
        secrets_keys = set(secrets_dict.keys())
        diff1 = secrets_keys.difference(secret_names_set)
        diff2 = secret_names_set.difference(secrets_keys)

        if len(diff1) > 0 or len(diff2) > 0:
            raise Exception(
                "secrets do not match: those secrets should be checked {0} {1}"
                .format(diff1, diff2))

        # We check everything is indeed a BigNumber, else we cast it
        for name, sec in secrets_dict.items():
            if not isinstance(sec, Bn):
                secrets_dict[name] = Bn.from_decimal(str(sec))

        return DLRepProver(self.generators, self.secret_names,
                              secrets_dict, self.lhs)
        
    def get_simulator(self):
        """ Returns an empty prover which can only simulate (via simulate_proof)
        """
        return DLRepProver(self.generators, self.secret_names, {}, self.lhs)
        
    def get_verifier(self):
        """
        :return: a DLRepVerifier for this proof
        """
        return DLRepVerifier(self.generators, self.secret_names,
                                self.lhs)

    def recompute_commitment(self, challenge, responses):
        """
        :param challenge: the petlib.bn.Bn representing the challenge
        :param responses: a list of petlib.bn.Bn
        :return: the commitment from the parameters
        """
        tab_g = self.generators
        y = self.lhs

        leftside = raise_powers(self.generators, responses) + (-challenge) * y
        return leftside

    def set_simulate(self):
        self.simulate = True



if __name__ == "__main__":  #A legit run in which we build the public info from random variables and pass everything to the process
    N = 5
    G = EcGroup(713)
    tab_g = []
    tab_g.append(G.generator())
    for i in range(1, N):
        randWord = randomword(30).encode("UTF-8")
        tab_g.append(G.hash_to_point(randWord))
    o = G.order()
    secrets_aliases = ["x1", "x2", "x3", "x4", "x5"]
    secrets_values = dict()
    secret_tab = [
    ]  #This array is only useful to compute the public info because zip doesn't take dicts. #spaghetti
    for wurd in secrets_aliases:  # we build N secrets
        secrets_values[wurd] = o.random()
        secret_tab.append(secrets_values[wurd])
    # peggy wishes to prove she knows the discrete logarithm equal to this value

    powers = [a * b for a, b in zip(secret_tab, tab_g)
              ]  # The Ys of which we will prove logarithm knowledge
    lhs = G.infinite()
    for y in powers:
        lhs += y

    dl_proof = DLRepProof(tab_g, secrets_aliases, lhs)
    dl_prover = dl_proof.get_prover(secrets_values)
    dl_verifier = dl_proof.get_verifier()

    dl_protocol = SigmaProtocol(dl_verifier, dl_prover)
    dl_protocol.run()