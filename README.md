# Propbox
A prop and costume management web application initially made for UAH.

## Propbox 1.0
[Release Notes](Propbox_1.0_Release_Notes.pdf)

## Installation Instructions
These instructions are for anyone from the UAH theater department who wants to use uah-propbox.appspot.com.

1. Navigate to the [site](https://uah-propbox.appspot.com), no setup required.

## Developer Installation Instructions
These instructions are for someone who wants to help contribute to the propbox project.
[Developer Guide](https://docs.google.com/document/d/150tjfQCVWj44AUbpQ-3HOCYtCxwx4G8quTkFvtUQkTU/edit?usp=sharing)

## Coding standards
[Standards Google Doc](https://docs.google.com/document/d/1ku-Ik56ovVwMY8OQi6WWcSATdy10ZfXoBIvz5S2qlDM/edit?usp=sharing)

## Files

| File Name           | Description                                   |
|---------------------|-----------------------------------------------|
| app.yaml            | yaml file for running the server.             |
| appengine_config.py | Python script for adding 3rd party imports.   |
| auth.py             | Script for user authentication.               |
| main.py             | Main handlers for web application.            |
| requirements.txt    | Server requirements.                          |
| utils.py 			  | Helpers for main.py 						  |
| warehouse_models.py | Framework for items stored in the database.   |

## Folders

| Folder Name    | Description                                             |
|----------------|---------------------------------------------------------|
| scripts/       | This folder contains scripts for use in various places. |
| stylesheets/   | This folder contains CSS files.                         |
| templates/     | This folder contains HTML templates.                    |
| static/        | This folder contains any static files that are not js,  |
|                | css, or jinja templates                                 |

## Acceptance Criteria
A code issue is acceptable/complete and can be closed when:
 |-------------------------------------------------------------|
 |The description's results section occur                      |
 |The result only occurs when the given section is valid       |
 |The result only occurs when the When section occurs in order |
 |Edge cases are covered properly and within reason            |
 |The change is pushed to the master branch on GitHub          |

Cards in ZenHub apply here.

## Done Done Criteria
A feature is officially resolved permanently when:
 |-------------------------------------------------------------|
 |Internal documentation is complete                           |
 |The code is well tested for edge cases                       |
 |UI is integrated successfully                                |
 |Group members agree it is done done                          |
 
 in addition to acceptance criteria being met.
 
 Cards in ZenHub DO NOT apply here.
