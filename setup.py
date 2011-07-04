from distutils.core import setup

setup(name='ct-jira-sanitizer',
      version='0.1pre',
      scripts=['sanitize.py'],
      data_files=[
        ('share/ct-jira-sanitizer', ['config.ini.sample']),
      ],
      install_requires=['ct'],
)
