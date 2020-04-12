#!/usr/bin/env python3

"""
	Nom,Prenom : Souissi, Nabil
	Matricule  : 000425495
"""

from sys import argv
from cplex import Cplex, SparsePair

def read_instance_file(filename):

    m = 0 # nombre de planches dispo
    L = 0 # Longueur fixe des planches
    li = [] # Les longueurs des panneaux
    qi = [] # Les quantités de panneaux par longueur

    index_line = 0
    file = open(filename, 'r')

    for line in file:

        index_line += 1
        liste = line.split(" ")
        
        if(index_line == 1):
            m = int(liste[1])
            L = float(liste[0])
        
        else:
            li.append(float(liste[0]))
            qi.append(int(liste[1]))

    file.close()

    return m,L,li,qi

def modelisation():

    # Variables 

    m, L, li, qi = read_instance_file(argv[1])

    # Modèle pour résoudre le problème de minimisation des planches utilisées 

    model = Cplex()
    model.set_results_stream(None)

    # Variables de décision du modèle

    model_variables = list(range(len(li)))
    model.variables.add(obj = [1 for j in model_variables])

    # Contraintes du modèle

    model_contraintes = range(len(qi))
    
    model.linear_constraints.add(  lin_expr = [SparsePair() for j in model_contraintes],
                                   senses   = ["G" for j in model_contraintes],
                                   rhs      = qi
                                )

    for var_index in model_variables:
        model.linear_constraints.set_coefficients(var_index, var_index, int(L / li[var_index]))

    # Modèle utilisé pour générer des pattern en utilisant 
    # la méthode Column generation de Gilmore-Gomory

    pattern_model = Cplex();
    pattern_model.set_results_stream(None)

    # Variable de décision

    panneaux_indices = range(len(li))
    pattern_model.variables.add(types = [pattern_model.variables.type.integer for j in panneaux_indices])

    pattern_model.variables.add(obj = [1], lb = [1], ub = [1])

    # L'unique contrainte ici est que la taille total des panneaux ne peut être
    # plus grande que la longueur de la planche L.
    pattern_model.linear_constraints.add(  lin_expr = [SparsePair(ind = panneaux_indices, val = li)],
                                           senses   = ["L"],
                                           rhs      = [L]
                                        )

    # Définir l'objectif (Minimisation)
    pattern_model.objective.set_sense(pattern_model.objective.sense.minimize)

    return m, model, pattern_model, model_contraintes, model_variables, panneaux_indices
    
def solve(model, pattern_model, model_contraintes, model_variables, panneaux_indices, m):

    Eps = 1e-3
    Cond = True

    # Column generation de Gilmore-Gomory

    while Cond:
        
        # On résout le modèle à chaque fois que l'on ajoute un nouveau pattern à tester
        model.solve()

        # L'objectif de cette fonction Z dites fonction économique est de trouver 
        # Un pattern qui serait utile pour résoudre notre problème tout en étant le plus optimal
        Z = map(lambda d: -d, model.solution.get_dual_values(list(model_contraintes)))        
        pattern_model.objective.set_linear(zip(panneaux_indices, Z))
        pattern_model.solve()

        # Si le coût de la fonction économique Z est non null alors nous avons atteint le pattern optimal
        if(pattern_model.solution.get_objective_value() > -Eps):
            Cond = False

        # Sinon nous ajoutons un nouveau pattern à la liste
        else:

            nouveau_pattern = pattern_model.solution.get_values(list(panneaux_indices))

            index = model.variables.get_num()
            model.variables.add(obj = [1.0] )
            model.linear_constraints.set_coefficients(zip(model_contraintes, [index for j in panneaux_indices], nouveau_pattern))
            model_variables.append(index)

    # Maintenant qu'on a le pattern optimal nous pouvons convertir nos variables en entier et 
    # tester à nouveau le modèle pour obtenir une solution final
    model.variables.set_types(zip(model_variables, [model.variables.type.integer for j in model_variables]))
    model.solve()

    # Afficher la solution du modèle
    print_solution(model, m)

    # Sauvegarder la solution dans un fichier CPLEX LP
    model.write("solution.lp")

def print_solution(model, m):

    print("\nLe nombre de planches utilisees : ", model.solution.get_objective_value())

    if(model.solution.get_objective_value() > m):
        print("Cette solution n'est pas valide puisqu'il faut plus de planches que celles disponibles !")

    else:
        print("\nLes variables utilises : \n")
        for sol  in range(model.variables.get_num()):
            print("Coupure ", str(sol), " : ", str(model.solution.get_values(sol)))

if __name__ == "__main__":

    if(len(argv) == 2):
        m, model, pattern_model, model_contraintes, model_variables, panneaux_indices = modelisation()
        solve(model, pattern_model, model_contraintes, model_variables, panneaux_indices, m)

    else:
        print("Erreur le format correct est le suivant : python generate_lp_instance.py [NOM_Fichier]")