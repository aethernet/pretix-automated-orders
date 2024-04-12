Pretix Automated Orders
==========================

This is a plugin for `pretix`.

Plugin for Pretix software that allows automated orders.

Given an event product and a list of emails, sends orders of that product to those emails.
(Good for sending free tickets or free products to customers.)

This Pretix plugin uses Celery, Redis and e-mail servers. Before you work on it, make sure you have a basic understanding of these tools.

How-to-Use
------------------

Install the plugin using pip.
In your event, go to the left settings tab and select plugins. Inside choose the "Pretix Automated Orders" plugin.

Build
---------

To build this plugin, run:


    make build


(NOTE: Make sure you have the correct version set in setup.cfg and the __init__.py file inside the plugin Django app folder.)

This will generate two files in the dist/ folder. You can use either to install the package using pip.

This package will be uploaded to PyPi anyways so it's available to anyone but you can also copy the .whl file to your Pretix installation and install it using pip.

Translations
------------

Run

    django-admin makemessages -l lang_code

to generate the translations file. After that use any translation software to translate using the .mo/.po files.

After the translations, run:

    django-admin compilemessages -l *lang_code*


(Run both commands inside the plugin app folder.)

Development
--------------

For development on this plugin, you can follow the documentation for plugin development provided on the Pretix documentation at their website.

There is an issue where Celery can't load the Pretix settings correctly when in development mode due to the way Pretix dynamically loads them using a .cfg file.

To bypass these problems, you can force the settings by editing the settings.py file inside the src/ directory of your Pretix development environment.

Pretix provides the Celery app in as src/pretix/celery_app.py.

In production, there shouldn't be any problem. Just install the plugin.

Development setup (Pretix)
----------------------------

1. Make sure that you have a working pretix development setup.

2. Clone this repository.

3. Activate the virtual environment you use for pretix development.

4. Execute ``python setup.py develop`` within this directory to register this application with pretix's plugin registry.

5. Execute ``make`` within this directory to compile translations.

6. Restart your local pretix server. You can now use the plugin from this repository for your events by enabling it in
   the 'plugins' tab in the settings.

This plugin has CI set up to enforce a few code style rules. To check locally, you need these packages installed::

    pip install flake8 isort black docformatter

To check your plugin for rule violations, run::

    docformatter --check -r .
    black --check .
    isort -c .
    flake8 .

You can auto-fix some of these issues by running::

    docformatter -r .
    isort .
    black .

To automatically check for these issues before you commit, you can run ``.install-hooks``.

License
-------

Copyright 2023 João Pires, Evolutio

Released under the terms of the Apache License 2.0
