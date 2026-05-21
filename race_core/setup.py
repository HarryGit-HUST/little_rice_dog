from setuptools import setup

package_name = 'race_core'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='root',
    maintainer_email='lijunhong1@xiaomi.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'vision_node = race_core.vision_node:main', # 如果你还有旧代码，留着备用
            'yellow_line_detector = race_core.yellow_line_detector:main',
            'main_brain = race_core.main_brain:main'
        ],
    },
)
