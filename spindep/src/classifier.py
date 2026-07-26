# // classifier.py
POTENTIAL_INFO = {

    "V2": {
        "type": "spin-spin",
        "description": "Axial-axial spin-spin interaction",
        "couplings": ["gAgA"]
    },

    "V3": {
        "type": "dipole-dipole",
        "description": "Dipole-dipole interaction",
        "couplings": ["gpgp", "gAgA"]
    },

    "V11": {
        "type": "spin-velocity",
        "description": "Axial-vector interaction",
        "couplings": ["gAgV"]
    },

    "V9+10": {
        "type": "monopole-dipole",
        "description": "Scalar-pseudoscalar interaction",
        "couplings": ["gPgS"]
    }
}


def classify_potential(potential):

    return POTENTIAL_INFO.get(
        potential,
        {
            "type": "unknown",
            "description": "unknown",
            "couplings": []
        }
    )
