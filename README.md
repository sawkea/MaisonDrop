# MaisonDrop

**MaisonDrop est une application web personnelle développée avec Python et Flask, hébergée localement et accessible depuis plusieurs appareils sur un réseau privé.**

Ce projet a pour objectif de réunir le développement web et la configuration de l'environnement d'hébergement, en accordant une attention particulière à l'accès sécurisé et à l'automatisation du démarrage.

## Installation de flask

* .venv\Scripts\python.exe -m pip install --upgrade pip (Outil de gestion de paquet python)
* .venv\Scripts\python.exe -m pip install Flask qrcode[pil] (micro-framework de développement web, léger et flexible écrit en Python)


## Présentation

MaisonDrop est un projet personnel développé et configuré parce que j'avais envie de déplacer les fichiers (pdf, photos, vidéos) depuis mon téléphone rapidement et simplement sur mon pc. Je l'utilise au quotidien.

L'application utilise Flask pour son fonctionnement côté serveur et Caddy comme reverse proxy afin de gérer les connexions HTTPS avant de les transmettre à Flask.

Le projet constitue une mise en pratique de plusieurs compétences en développement Python, configuration serveur, réseau local et automatisation sous Windows.

## Fonctionnalités et configuration

- **Application web Python** : utilisation de Flask pour exécuter l'application.
- **Point d'accès de connexion** : page accessible via la route `/login`.
- **HTTPS** : gestion des connexions chiffrées grâce à Caddy et à une autorité de certification locale.
- **Reverse proxy** : transmission des requêtes HTTPS vers le serveur Flask.
- **Accès multi-appareils** : utilisation depuis un navigateur sur PC ou iPhone connecté au même réseau local.
- **Adresse IP réservée** : configuration DHCP afin de conserver une adresse locale stable.
- **Démarrage automatisé** : utilisation de scripts PowerShell et de tâches planifiées Windows pour lancer les services.
- **Configuration du pare-feu** : autorisation des connexions HTTPS entrantes sur le réseau privé.

## Technologies utilisées

* Python : Langage principal 
* Flask : Application web côté serveur 
* Caddy : Serveur web et reverse proxy HTTPS 
* TLS / HTTPS : Chiffrement des connexions 
* PowerShell : Automatisation et lancement des services 
* Planificateur de tâches Windows : Démarrage automatique 
* Réseau local / DHCP : Accès depuis plusieurs appareils 

## Architecture

Le fonctionnement général repose sur deux services :

```text
Navigateur web (PC ou iPhone)
              |
              | HTTPS - port 443
              v
           Caddy
        Reverse proxy
              |
              | HTTP local - port 8000
              v
         Application
          Flask
```

Caddy reçoit les connexions HTTPS et les transmet à Flask sur le port local `8000`. Cette séparation permet de distinguer le fonctionnement de l'application de la gestion des connexions sécurisées.

## Environnement d'exécution

Le projet est actuellement configuré pour fonctionner sur un ordinateur Windows connecté à un réseau privé.

L'accès depuis un autre appareil s'effectue à l'aide de l'adresse IP locale du PC. Le certificat racine de l'autorité locale doit être installé et approuvé sur les appareils clients pour que le navigateur puisse vérifier correctement le certificat HTTPS.

Le PC doit être allumé et les services nécessaires doivent être démarrés.

## Installation et configuration

La configuration actuelle dépend de l'environnement Windows sur lequel le projet est exécuté.

Pour reproduire l'installation, il faut notamment :

1. Installer Python et les dépendances du projet.
2. Configurer et lancer l'application Flask.
3. Installer Caddy et configurer le reverse proxy vers Flask.
4. Configurer le certificat TLS local et la confiance sur les appareils clients.
5. Préparer les règles de pare-feu adaptées au réseau privé.
6. Configurer les scripts PowerShell et les tâches planifiées pour automatiser le démarrage.

Les chemins d'accès, les paramètres réseau et les tâches planifiées doivent être adaptés à la machine utilisée.

## Sécurité

MaisonDrop est conçu et configuré pour un usage sur un réseau local privé.

- Les connexions entre les navigateurs et Caddy utilisent HTTPS.
- Flask est accessible sur le port local `8000` et Caddy gère l'accès HTTPS.
- L'accès réseau est limité par la configuration du pare-feu Windows.
- Le certificat racine privé ne doit pas être partagé publiquement.
- Aucune redirection de port vers Internet n'est nécessaire pour l'utilisation prévue sur le réseau local.

Le HTTPS sécurise les échanges avec le serveur, mais ne remplace pas les protections applicatives, telles que l'authentification, la gestion des sessions et le contrôle des accès.

## Objectifs du projet

MaisonDrop est un projet personnel d'apprentissage et de mise en pratique. Il me permet d'approfondir mes compétences en développement web Python, en configuration de serveurs, en sécurité des connexions et en administration d'un environnement Windows.

Il illustre également ma capacité à intégrer plusieurs technologies, à automatiser des tâches et à diagnostiquer des problèmes sur l'ensemble d'une chaîne applicative.

## Utilisation de l'intelligence artificielle

J'ai utilisé l'IA comme outil d'aide au développement pour améliorer mon code, comprendre les erreurs rencontrées et configurer certains éléments techniques.

Cette démarche m'a permis d'apprendre et de tester différentes solutions.

## Auteur

Sonia Hoareau

