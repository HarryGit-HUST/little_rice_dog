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
            # 格式：'你在终端敲的名字 = 文件夹名.文件名:执行的函数名'
            'vision_node = race_core.vision_node:main',
            'main_brain = race_core.main_brain:main'
        ],
    },
)
