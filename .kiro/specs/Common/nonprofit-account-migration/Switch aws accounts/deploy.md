un sam deploy \
  sam deploy \
    --stack-name h-dcn \
    --region eu-west-1 \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --resolve-s3 \
    --resolve-image-repos \
    --no-confirm-changeset \
    --no-fail-on-empty-changeset \
    --parameter-overrides \
      Environment=prod \
      Table=Producten \
      Region=eu-west-1 \
      MembersTable=Members \
      PaymentsTable=Payments \
      EventsTable=Events \
      MembershipsTable=Memberships \
      CartsTable=Carts \
      OrdersTable=Orders \
      ParametersTable=Parameters
  shell: /usr/bin/bash -e {0}
  env:
    pythonLocation: /opt/hostedtoolcache/Python/3.11.15/x64
    PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.11.15/x64/lib/pkgconfig
    Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.11.15/x64
    Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.11.15/x64
    Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.11.15/x64
    LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.11.15/x64/lib
    AWS_DEFAULT_REGION: eu-west-1
    AWS_REGION: eu-west-1
    AWS_ACCESS_KEY_ID: ***
    AWS_SECRET_ACCESS_KEY: ***
    AWS_SESSION_TOKEN: ***
  
	Managed S3 bucket: aws-sam-cli-managed-default-samclisourcebucket-blif0fm8tjah
	Auto resolution of buckets can be turned off by setting resolve_s3=False
	To use a specific S3 bucket, set --s3-bucket=<bucket_name>
	Above settings can be stored in samconfig.toml
	File with same data already exists at 63f28bea9be07cf36161f8e9382b148f.template, skipping upload
	Uploading to 4e41e11389fab8628ab00fbb4d5e85fd  7553 / 7553  (100.00%)
	Uploading to 60899aef195964360197e1e73181b9eb  5835 / 5835  (100.00%)
	Uploading to 24b4db44c9a2ab308346c93fd567f50e  1793 / 1793  (100.00%)
	Uploading to 0dce8e4ed604f35d8108f65d58025dd5  1048576 / 15731006  (6.67%)
	Uploading to 0dce8e4ed604f35d8108f65d58025dd5  2097152 / 15731006  (13.33%)
	Uploading to 0dce8e4ed604f35d8108f65d58025dd5  3145728 / 15731006  (20.00%)
	Uploading to 0dce8e4ed604f35d8108f65d58025dd5  4194304 / 15731006  (26.66%)
	Uploading to 0dce8e4ed604f35d8108f65d58025dd5  5242880 / 15731006  (33.33%)
	Uploading to 0dce8e4ed604f35d8108f65d58025dd5  6291456 / 15731006  (39.99%)
	Uploading to 0dce8e4ed604f35d8108f65d58025dd5  7340032 / 15731006  (46.66%)
	Uploading to 0dce8e4ed604f35d8108f65d58025dd5  8388608 / 15731006  (53.33%)
	Uploading to 0dce8e4ed604f35d8108f65d58025dd5  9437184 / 15731006  (59.99%)
	Uploading to 0dce8e4ed604f35d8108f65d58025dd5  10485760 / 15731006  (66.66%)
	Uploading to 0dce8e4ed604f35d8108f65d58025dd5  11534336 / 15731006  (73.32%)
	Uploading to 0dce8e4ed604f35d8108f65d58025dd5  12582912 / 15731006  (79.99%)
	Uploading to 0dce8e4ed604f35d8108f65d58025dd5  13631488 / 15731006  (86.65%)
	Uploading to 0dce8e4ed604f35d8108f65d58025dd5  14680064 / 15731006  (93.32%)
	Uploading to 0dce8e4ed604f35d8108f65d58025dd5  15728640 / 15731006  (99.98%)
	Uploading to 0dce8e4ed604f35d8108f65d58025dd5  15731006 / 15731006  (100.00%)
	Uploading to 3a472cdd83f649d6bcf56c5c31aa46d8  3093 / 3093  (100.00%)
	Uploading to 0c2b504e4e7395a4e7f7b57df3da9053  618626 / 618626  (100.00%)
	Uploading to 5a54d2788d30e0a2b3347125c2b48c2a  618546 / 618546  (100.00%)
	Uploading to 209c3984847a7cd81429b54eff56df50  618594 / 618594  (100.00%)
	Uploading to 3d8396bfb83d704b1a5b4380e1964027  618509 / 618509  (100.00%)
	Uploading to e8b1aba92791861024a96e640d24a762  2829 / 2829  (100.00%)
	Uploading to b95f041d9030367f6d5b0061dd2c3baa  2765 / 2765  (100.00%)
	Uploading to 10dde8c1815d88e90597f6ea26f3b33b  1595 / 1595  (100.00%)
	Uploading to 1997fc9b10807889f044531f28e97629  3596 / 3596  (100.00%)
	Uploading to 763badec694f2dcc46636e45573ea4c1  1478 / 1478  (100.00%)
	Uploading to 8b8c3534f726d2bb6a99d10edd4d6963  11143 / 11143  (100.00%)
	Uploading to 2bb3b08a63aade38e70c734e9c81da08  23668 / 23668  (100.00%)
	Uploading to 3df5de1ebb1e01e40d200d12c8d348fd  947 / 947  (100.00%)
	Uploading to 57c8bccb76e65f993367b2c85c11a5f3  3402 / 3402  (100.00%)
	Uploading to 9abbc996cba6873528530482ce11fe6c  1805 / 1805  (100.00%)
	Uploading to 6e4ff3aab1f542f52b0197c9eb457fa3  1796 / 1796  (100.00%)
	Uploading to eb7369aed55e8a8140a064c749695503  3860 / 3860  (100.00%)
	Uploading to 66399c7970c790347aef5e20fb5810b9  2558 / 2558  (100.00%)
	Uploading to ac326caac94aa07b43cb0e0558edd2d2  1850 / 1850  (100.00%)
	Uploading to c28374551a810a3d82409c2aeac1a038  1452 / 1452  (100.00%)
	Uploading to 07ba701d97fd7c5290636620b27c2f57  2768 / 2768  (100.00%)
	Uploading to 0a659658f461d98baef16a10069215ee  1048576 / 15784312  (6.64%)
	Uploading to 0a659658f461d98baef16a10069215ee  2097152 / 15784312  (13.29%)
	Uploading to 0a659658f461d98baef16a10069215ee  3145728 / 15784312  (19.93%)
	Uploading to 0a659658f461d98baef16a10069215ee  4194304 / 15784312  (26.57%)
	Uploading to 0a659658f461d98baef16a10069215ee  5242880 / 15784312  (33.22%)
	Uploading to 0a659658f461d98baef16a10069215ee  6291456 / 15784312  (39.86%)
	Uploading to 0a659658f461d98baef16a10069215ee  7340032 / 15784312  (46.50%)
	Uploading to 0a659658f461d98baef16a10069215ee  8388608 / 15784312  (53.15%)
	Uploading to 0a659658f461d98baef16a10069215ee  8444280 / 15784312  (53.50%)
	Uploading to 0a659658f461d98baef16a10069215ee  9492856 / 15784312  (60.14%)
	Uploading to 0a659658f461d98baef16a10069215ee  10541432 / 15784312  (66.78%)
	Uploading to 0a659658f461d98baef16a10069215ee  11590008 / 15784312  (73.43%)
	Uploading to 0a659658f461d98baef16a10069215ee  12638584 / 15784312  (80.07%)
	Uploading to 0a659658f461d98baef16a10069215ee  13687160 / 15784312  (86.71%)
	Uploading to 0a659658f461d98baef16a10069215ee  14735736 / 15784312  (93.36%)
	Uploading to 0a659658f461d98baef16a10069215ee  15784312 / 15784312  (100.00%)
	Uploading to dcfa894e71e3036706c474318c0a9fe3  996 / 996  (100.00%)
	Uploading to 4a62ae37b57b33c98ed9e9c9d00a23e1  1014 / 1014  (100.00%)
	Uploading to a6d4cf034fae1968f6b2ed9cb8a341b9  1080 / 1080  (100.00%)
	Uploading to 2b1ae99996e7a8b8ff4e9fbed838c9fa  1195 / 1195  (100.00%)
	Uploading to a40a4bcd6b73a586cbbd3c14c6e79aed  949 / 949  (100.00%)
	Uploading to fe579bc4de0c5f64fff7d771baab2e7e  2163 / 2163  (100.00%)
	Uploading to a192b164afd6b3eaf512b85adaae19fd  2490 / 2490  (100.00%)
	Uploading to c0e8d8f4e423200b61bcab2ce28a838e  2404 / 2404  (100.00%)
	Uploading to 64bb5e7328c637f865342795db006a53  2950 / 2950  (100.00%)
	Uploading to 719fb21351e9139ada2722154ee8d2e8  3603 / 3603  (100.00%)
	Uploading to e78440b244baa94afc66d8f8db61d783  3278 / 3278  (100.00%)
	Uploading to 992204efe1329a5aeed5a28c529fc9ca  3159 / 3159  (100.00%)
	Uploading to 6c75768915f12eaa50b6981f8db62d6a  3531 / 3531  (100.00%)
The push refers to repository [506221081911.dkr.ecr.eu-west-1.amazonaws.com/hdcn6143bf32/generateorderpdffunction42805cd9repo]

92db1471b910: Preparing 

df4b086fd185: Preparing 

60a6b6b96858: Preparing 

5acffd4a5608: Preparing 

4d2e36b73e9a: Preparing 

27a683df4e27: Preparing 

5895227161a0: Preparing 

2aad2b6263bb: Preparing 

8f863789c1a6: Preparing 

ed626ac81049: Preparing 

cc26948106da: Preparing 

d57a341501a2: Preparing 

27a683df4e27: Waiting 

5895227161a0: Waiting 

2aad2b6263bb: Waiting 

8f863789c1a6: Waiting 

ed626ac81049: Waiting 

cc26948106da: Waiting 

d57a341501a2: Waiting 

4d2e36b73e9a: Pushing [>                                                  ]     512B/32.51kB

92db1471b910: Pushing [==================================================>]     512B

92db1471b910: Pushing [==================================================>]  3.072kB

4d2e36b73e9a: Pushing [==================================================>]  37.38kB

5acffd4a5608: Pushing [==================================================>]     512B

5acffd4a5608: Pushing [==================================================>]  3.072kB

df4b086fd185: Pushing [=>                                                 ]     512B/15kB

df4b086fd185: Pushing [==================================================>]  17.92kB

60a6b6b96858: Pushing [>                                                  ]    547kB/70.45MB

60a6b6b96858: Pushing [>                                                  ]  1.074MB/70.45MB

60a6b6b96858: Pushing [=>                                                 ]  1.627MB/70.45MB

60a6b6b96858: Pushing [=>                                                 ]  2.158MB/70.45MB

60a6b6b96858: Pushing [==>                                                ]  3.247MB/70.45MB

60a6b6b96858: Pushing [====>                                              ]  6.032MB/70.45MB

60a6b6b96858: Pushing [======>                                            ]   8.73MB/70.45MB

60a6b6b96858: Pushing [========>                                          ]   12.6MB/70.45MB

60a6b6b96858: Pushing [===========>                                       ]   15.8MB/70.45MB

60a6b6b96858: Pushing [=============>                                     ]  19.13MB/70.45MB

60a6b6b96858: Pushing [================>                                  ]  22.97MB/70.45MB

5acffd4a5608: Pushed 

4d2e36b73e9a: Pushed 

60a6b6b96858: Pushing [==================>                                ]  26.31MB/70.45MB

92db1471b910: Pushed 

60a6b6b96858: Pushing [====================>                              ]  29.56MB/70.45MB

60a6b6b96858: Pushing [=======================>                           ]  32.85MB/70.45MB

60a6b6b96858: Pushing [=========================>                         ]  36.13MB/70.45MB

60a6b6b96858: Pushing [===========================>                       ]  39.38MB/70.45MB

df4b086fd185: Pushed 

60a6b6b96858: Pushing [==============================>                    ]  42.64MB/70.45MB

60a6b6b96858: Pushing [================================>                  ]  45.43MB/70.45MB

60a6b6b96858: Pushing [==================================>                ]  48.21MB/70.45MB

60a6b6b96858: Pushing [====================================>              ]  50.98MB/70.45MB

27a683df4e27: Pushing [>                                                  ]  532.5kB/185.1MB

60a6b6b96858: Pushing [======================================>            ]  54.22MB/70.45MB

27a683df4e27: Pushing [>                                                  ]  1.647MB/185.1MB

5895227161a0: Pushing [>                                                  ]  1.024kB/56.94kB

5895227161a0: Pushing [==================================================>]  62.98kB

60a6b6b96858: Pushing [========================================>          ]  56.92MB/70.45MB

27a683df4e27: Pushing [>                                                  ]  2.204MB/185.1MB

60a6b6b96858: Pushing [==========================================>        ]  59.64MB/70.45MB

27a683df4e27: Pushing [>                                                  ]  2.761MB/185.1MB

60a6b6b96858: Pushing [===========================================>       ]  61.83MB/70.45MB

27a683df4e27: Pushing [=>                                                 ]  4.432MB/185.1MB

60a6b6b96858: Pushing [=============================================>     ]  64.02MB/70.45MB

27a683df4e27: Pushing [=>                                                 ]   6.66MB/185.1MB

2aad2b6263bb: Pushing [>                                                  ]  527.1kB/387.7MB

60a6b6b96858: Pushing [===============================================>   ]  66.69MB/70.45MB

8f863789c1a6: Pushing [>                                                  ]  100.9kB/9.233MB

27a683df4e27: Pushing [==>                                                ]  9.421MB/185.1MB

2aad2b6263bb: Pushing [>                                                  ]   1.06MB/387.7MB

60a6b6b96858: Pushing [=================================================> ]  69.39MB/70.45MB

27a683df4e27: Pushing [===>                                               ]  12.14MB/185.1MB

60a6b6b96858: Pushing [==================================================>]  71.56MB

2aad2b6263bb: Pushing [>                                                  ]  1.617MB/387.7MB

27a683df4e27: Pushing [====>                                              ]  14.82MB/185.1MB

8f863789c1a6: Pushing [=>                                                 ]  199.2kB/9.233MB

2aad2b6263bb: Pushing [>                                                  ]  2.146MB/387.7MB

27a683df4e27: Pushing [====>                                              ]  17.56MB/185.1MB

8f863789c1a6: Pushing [==>                                                ]  395.8kB/9.233MB

2aad2b6263bb: Pushing [>                                                  ]   3.26MB/387.7MB

27a683df4e27: Pushing [=====>                                             ]  20.23MB/185.1MB

8f863789c1a6: Pushing [==>                                                ]  494.1kB/9.233MB

2aad2b6263bb: Pushing [>                                                  ]  4.931MB/387.7MB

27a683df4e27: Pushing [======>                                            ]  23.49MB/185.1MB

2aad2b6263bb: Pushing [>                                                  ]  7.716MB/387.7MB

8f863789c1a6: Pushing [===>                                               ]  690.7kB/9.233MB

27a683df4e27: Pushing [=======>                                           ]  26.69MB/185.1MB

8f863789c1a6: Pushing [=========>                                         ]  1.772MB/9.233MB

2aad2b6263bb: Pushing [=>                                                 ]  9.945MB/387.7MB

27a683df4e27: Pushing [========>                                          ]  30.38MB/185.1MB

27a683df4e27: Pushing [========>                                          ]  33.01MB/185.1MB

8f863789c1a6: Pushing [==============>                                    ]  2.657MB/9.233MB

2aad2b6263bb: Pushing [=>                                                 ]  12.17MB/387.7MB

8f863789c1a6: Pushing [=========================>                         ]  4.623MB/9.233MB

27a683df4e27: Pushing [=========>                                         ]   36.2MB/185.1MB

2aad2b6263bb: Pushing [=>                                                 ]  14.96MB/387.7MB

8f863789c1a6: Pushing [======================================>            ]  7.179MB/9.233MB

27a683df4e27: Pushing [==========>                                        ]  39.41MB/185.1MB

2aad2b6263bb: Pushing [==>                                                ]  17.74MB/387.7MB

5895227161a0: Pushed 

8f863789c1a6: Pushing [=================================================> ]  9.145MB/9.233MB

8f863789c1a6: Pushing [==================================================>]  9.236MB

2aad2b6263bb: Pushing [==>                                                ]  20.53MB/387.7MB

27a683df4e27: Pushing [===========>                                       ]  43.21MB/185.1MB

2aad2b6263bb: Pushing [===>                                               ]   23.3MB/387.7MB

27a683df4e27: Pushing [============>                                      ]  45.42MB/185.1MB

2aad2b6263bb: Pushing [===>                                               ]  25.44MB/387.7MB

27a683df4e27: Pushing [============>                                      ]  47.58MB/185.1MB

2aad2b6263bb: Pushing [===>                                               ]  28.14MB/387.7MB

27a683df4e27: Pushing [=============>                                     ]  49.75MB/185.1MB

27a683df4e27: Pushing [==============>                                    ]   53.6MB/185.1MB

2aad2b6263bb: Pushing [====>                                              ]  31.41MB/387.7MB

60a6b6b96858: Pushed 

27a683df4e27: Pushing [===============>                                   ]  58.02MB/185.1MB

2aad2b6263bb: Pushing [====>                                              ]  34.63MB/387.7MB

27a683df4e27: Pushing [=================>                                 ]  62.95MB/185.1MB

2aad2b6263bb: Pushing [====>                                              ]  37.84MB/387.7MB

27a683df4e27: Pushing [=================>                                 ]  65.63MB/185.1MB

2aad2b6263bb: Pushing [=====>                                             ]  41.06MB/387.7MB

27a683df4e27: Pushing [==================>                                ]   68.4MB/185.1MB

2aad2b6263bb: Pushing [=====>                                             ]  44.27MB/387.7MB

27a683df4e27: Pushing [===================>                               ]  70.56MB/185.1MB

ed626ac81049: Pushing [==================================================>]     512B

ed626ac81049: Pushing [==================================================>]   2.56kB

2aad2b6263bb: Pushing [======>                                            ]  46.98MB/387.7MB

27a683df4e27: Pushing [===================>                               ]  72.72MB/185.1MB

2aad2b6263bb: Pushing [======>                                            ]  50.32MB/387.7MB

27a683df4e27: Pushing [====================>                              ]  75.41MB/185.1MB

2aad2b6263bb: Pushing [======>                                            ]  53.66MB/387.7MB

27a683df4e27: Pushing [=====================>                             ]  78.19MB/185.1MB

2aad2b6263bb: Pushing [=======>                                           ]     57MB/387.7MB

27a683df4e27: Pushing [======================>                            ]  81.53MB/185.1MB

8f863789c1a6: Pushed 

2aad2b6263bb: Pushing [=======>                                           ]  60.35MB/387.7MB

27a683df4e27: Pushing [======================>                            ]  84.87MB/185.1MB

cc26948106da: Pushing [==>                                                ]  33.79kB/659.1kB

2aad2b6263bb: Pushing [========>                                          ]  63.69MB/387.7MB

27a683df4e27: Pushing [=======================>                           ]  87.66MB/185.1MB

2aad2b6263bb: Pushing [========>                                          ]  67.03MB/387.7MB

27a683df4e27: Pushing [========================>                          ]     91MB/185.1MB

2aad2b6263bb: Pushing [=========>                                         ]  70.37MB/387.7MB

27a683df4e27: Pushing [=========================>                         ]  93.79MB/185.1MB

cc26948106da: Pushing [================================>                  ]    427kB/659.1kB

2aad2b6263bb: Pushing [=========>                                         ]  73.72MB/387.7MB

cc26948106da: Pushing [==================================================>]  661.5kB

27a683df4e27: Pushing [==========================>                        ]  97.13MB/185.1MB

2aad2b6263bb: Pushing [=========>                                         ]   76.5MB/387.7MB

27a683df4e27: Pushing [==========================>                        ]  99.91MB/185.1MB

2aad2b6263bb: Pushing [==========>                                        ]  79.29MB/387.7MB

27a683df4e27: Pushing [===========================>                       ]  102.7MB/185.1MB

2aad2b6263bb: Pushing [==========>                                        ]  82.63MB/387.7MB

27a683df4e27: Pushing [============================>                      ]  104.9MB/185.1MB

2aad2b6263bb: Pushing [===========>                                       ]  85.97MB/387.7MB

27a683df4e27: Pushing [=============================>                     ]  107.6MB/185.1MB

2aad2b6263bb: Pushing [===========>                                       ]  89.31MB/387.7MB

27a683df4e27: Pushing [=============================>                     ]  110.3MB/185.1MB

2aad2b6263bb: Pushing [===========>                                       ]  92.66MB/387.7MB

27a683df4e27: Pushing [==============================>                    ]    113MB/185.1MB

2aad2b6263bb: Pushing [============>                                      ]     96MB/387.7MB

27a683df4e27: Pushing [===============================>                   ]  115.7MB/185.1MB

ed626ac81049: Pushed 

2aad2b6263bb: Pushing [============>                                      ]  99.34MB/387.7MB

27a683df4e27: Pushing [===============================>                   ]  118.4MB/185.1MB

27a683df4e27: Pushing [================================>                  ]  120.6MB/185.1MB

2aad2b6263bb: Pushing [=============>                                     ]  102.7MB/387.7MB

2aad2b6263bb: Pushing [=============>                                     ]  105.5MB/387.7MB

d57a341501a2: Pushing [>                                                  ]    533kB/304.2MB

27a683df4e27: Pushing [=================================>                 ]  122.8MB/185.1MB

2aad2b6263bb: Pushing [=============>                                     ]  108.3MB/387.7MB

d57a341501a2: Pushing [>                                                  ]  1.058MB/304.2MB

27a683df4e27: Pushing [=================================>                 ]    125MB/185.1MB

2aad2b6263bb: Pushing [==============>                                    ]  111.6MB/387.7MB

d57a341501a2: Pushing [>                                                  ]  1.603MB/304.2MB

27a683df4e27: Pushing [==================================>                ]  127.3MB/185.1MB

2aad2b6263bb: Pushing [==============>                                    ]  114.4MB/387.7MB

d57a341501a2: Pushing [>                                                  ]  2.714MB/304.2MB

27a683df4e27: Pushing [==================================>                ]  129.4MB/185.1MB

2aad2b6263bb: Pushing [===============>                                   ]  117.2MB/387.7MB

cc26948106da: Pushed 

d57a341501a2: Pushing [>                                                  ]  4.863MB/304.2MB

27a683df4e27: Pushing [===================================>               ]  132.6MB/185.1MB

2aad2b6263bb: Pushing [===============>                                   ]    120MB/387.7MB

d57a341501a2: Pushing [=>                                                 ]  7.034MB/304.2MB

27a683df4e27: Pushing [====================================>              ]  135.3MB/185.1MB

2aad2b6263bb: Pushing [===============>                                   ]  122.7MB/387.7MB

d57a341501a2: Pushing [=>                                                 ]  9.229MB/304.2MB

27a683df4e27: Pushing [=====================================>             ]  137.4MB/185.1MB

2aad2b6263bb: Pushing [================>                                  ]  125.5MB/387.7MB

d57a341501a2: Pushing [=>                                                 ]  11.38MB/304.2MB

27a683df4e27: Pushing [======================================>            ]  141.2MB/185.1MB

2aad2b6263bb: Pushing [================>                                  ]  128.3MB/387.7MB

d57a341501a2: Pushing [==>                                                ]  13.54MB/304.2MB

27a683df4e27: Pushing [=======================================>           ]  146.1MB/185.1MB

2aad2b6263bb: Pushing [================>                                  ]  131.1MB/387.7MB

d57a341501a2: Pushing [==>                                                ]  16.22MB/304.2MB

27a683df4e27: Pushing [========================================>          ]  149.4MB/185.1MB

2aad2b6263bb: Pushing [=================>                                 ]  133.9MB/387.7MB

d57a341501a2: Pushing [===>                                               ]  18.38MB/304.2MB

27a683df4e27: Pushing [=========================================>         ]  152.2MB/185.1MB

2aad2b6263bb: Pushing [=================>                                 ]  137.2MB/387.7MB

d57a341501a2: Pushing [===>                                               ]  21.72MB/304.2MB

27a683df4e27: Pushing [=========================================>         ]  155.4MB/185.1MB

2aad2b6263bb: Pushing [==================>                                ]    140MB/387.7MB

d57a341501a2: Pushing [====>                                              ]  24.51MB/304.2MB

27a683df4e27: Pushing [==========================================>        ]  158.1MB/185.1MB

2aad2b6263bb: Pushing [==================>                                ]  142.8MB/387.7MB

d57a341501a2: Pushing [====>                                              ]  27.85MB/304.2MB

27a683df4e27: Pushing [===========================================>       ]  160.7MB/185.1MB

2aad2b6263bb: Pushing [==================>                                ]    146MB/387.7MB

d57a341501a2: Pushing [=====>                                             ]  30.64MB/304.2MB

27a683df4e27: Pushing [============================================>      ]  163.4MB/185.1MB

2aad2b6263bb: Pushing [===================>                               ]  149.3MB/387.7MB

d57a341501a2: Pushing [=====>                                             ]  33.42MB/304.2MB

2aad2b6263bb: Pushing [===================>                               ]    153MB/387.7MB

27a683df4e27: Pushing [============================================>      ]  166.1MB/185.1MB

d57a341501a2: Pushing [=====>                                             ]  36.21MB/304.2MB

2aad2b6263bb: Pushing [====================>                              ]  156.7MB/387.7MB

27a683df4e27: Pushing [=============================================>     ]  168.8MB/185.1MB

d57a341501a2: Pushing [======>                                            ]  39.55MB/304.2MB

2aad2b6263bb: Pushing [====================>                              ]  160.1MB/387.7MB

27a683df4e27: Pushing [==============================================>    ]    171MB/185.1MB

d57a341501a2: Pushing [======>                                            ]  42.33MB/304.2MB

27a683df4e27: Pushing [==============================================>    ]  173.1MB/185.1MB

2aad2b6263bb: Pushing [====================>                              ]  162.8MB/387.7MB

d57a341501a2: Pushing [=======>                                           ]  45.12MB/304.2MB

2aad2b6263bb: Pushing [=====================>                             ]    166MB/387.7MB

27a683df4e27: Pushing [===============================================>   ]  175.7MB/185.1MB

d57a341501a2: Pushing [=======>                                           ]  47.91MB/304.2MB

27a683df4e27: Pushing [================================================>  ]  177.8MB/185.1MB

2aad2b6263bb: Pushing [=====================>                             ]  169.7MB/387.7MB

d57a341501a2: Pushing [========>                                          ]  50.69MB/304.2MB

2aad2b6263bb: Pushing [======================>                            ]  172.4MB/387.7MB

27a683df4e27: Pushing [================================================>  ]  180.4MB/185.1MB

d57a341501a2: Pushing [========>                                          ]  54.03MB/304.2MB

27a683df4e27: Pushing [=================================================> ]  184.3MB/185.1MB

2aad2b6263bb: Pushing [======================>                            ]  175.1MB/387.7MB

d57a341501a2: Pushing [=========>                                         ]  56.82MB/304.2MB

27a683df4e27: Pushing [==================================================>]  187.7MB

2aad2b6263bb: Pushing [======================>                            ]  177.3MB/387.7MB

d57a341501a2: Pushing [=========>                                         ]   59.6MB/304.2MB

2aad2b6263bb: Pushing [=======================>                           ]  179.5MB/387.7MB

27a683df4e27: Pushing [==================================================>]    191MB

d57a341501a2: Pushing [==========>                                        ]  62.39MB/304.2MB

2aad2b6263bb: Pushing [=======================>                           ]  181.7MB/387.7MB

27a683df4e27: Pushing [==================================================>]  194.2MB

d57a341501a2: Pushing [==========>                                        ]  65.17MB/304.2MB

27a683df4e27: Pushing [==================================================>]  195.9MB

2aad2b6263bb: Pushing [=======================>                           ]  183.8MB/387.7MB

d57a341501a2: Pushing [===========>                                       ]  67.96MB/304.2MB

2aad2b6263bb: Pushing [=======================>                           ]  186.1MB/387.7MB

d57a341501a2: Pushing [===========>                                       ]   71.3MB/304.2MB

2aad2b6263bb: Pushing [========================>                          ]  188.8MB/387.7MB

d57a341501a2: Pushing [============>                                      ]  74.64MB/304.2MB

2aad2b6263bb: Pushing [========================>                          ]  191.5MB/387.7MB

d57a341501a2: Pushing [============>                                      ]  77.99MB/304.2MB

2aad2b6263bb: Pushing [=========================>                         ]  194.3MB/387.7MB

d57a341501a2: Pushing [=============>                                     ]  81.33MB/304.2MB

2aad2b6263bb: Pushing [=========================>                         ]  198.1MB/387.7MB

d57a341501a2: Pushing [=============>                                     ]  84.67MB/304.2MB

2aad2b6263bb: Pushing [=========================>                         ]  201.3MB/387.7MB

d57a341501a2: Pushing [==============>                                    ]  88.01MB/304.2MB

2aad2b6263bb: Pushing [==========================>                        ]    204MB/387.7MB

d57a341501a2: Pushing [===============>                                   ]  91.36MB/304.2MB

2aad2b6263bb: Pushing [==========================>                        ]  207.2MB/387.7MB

d57a341501a2: Pushing [===============>                                   ]   94.7MB/304.2MB

2aad2b6263bb: Pushing [===========================>                       ]  210.4MB/387.7MB

d57a341501a2: Pushing [================>                                  ]  98.04MB/304.2MB

2aad2b6263bb: Pushing [===========================>                       ]  214.1MB/387.7MB

d57a341501a2: Pushing [================>                                  ]  100.8MB/304.2MB

2aad2b6263bb: Pushing [============================>                      ]  218.5MB/387.7MB

d57a341501a2: Pushing [================>                                  ]  103.1MB/304.2MB

2aad2b6263bb: Pushing [============================>                      ]  221.7MB/387.7MB

d57a341501a2: Pushing [=================>                                 ]  105.8MB/304.2MB

d57a341501a2: Pushing [=================>                                 ]  108.6MB/304.2MB

2aad2b6263bb: Pushing [=============================>                     ]  224.9MB/387.7MB

27a683df4e27: Pushed 

2aad2b6263bb: Pushing [=============================>                     ]  227.6MB/387.7MB

d57a341501a2: Pushing [==================>                                ]    112MB/304.2MB

2aad2b6263bb: Pushing [=============================>                     ]  230.2MB/387.7MB

d57a341501a2: Pushing [==================>                                ]  115.3MB/304.2MB

2aad2b6263bb: Pushing [==============================>                    ]  232.9MB/387.7MB

d57a341501a2: Pushing [===================>                               ]  118.7MB/304.2MB

2aad2b6263bb: Pushing [==============================>                    ]  236.2MB/387.7MB

d57a341501a2: Pushing [====================>                              ]    122MB/304.2MB

2aad2b6263bb: Pushing [==============================>                    ]  238.9MB/387.7MB

d57a341501a2: Pushing [====================>                              ]  124.8MB/304.2MB

2aad2b6263bb: Pushing [===============================>                   ]  241.6MB/387.7MB

d57a341501a2: Pushing [====================>                              ]  127.6MB/304.2MB

2aad2b6263bb: Pushing [===============================>                   ]  244.2MB/387.7MB

d57a341501a2: Pushing [=====================>                             ]  130.3MB/304.2MB

2aad2b6263bb: Pushing [===============================>                   ]    247MB/387.7MB

d57a341501a2: Pushing [=====================>                             ]  133.1MB/304.2MB

2aad2b6263bb: Pushing [================================>                  ]  249.6MB/387.7MB

d57a341501a2: Pushing [======================>                            ]  136.2MB/304.2MB

2aad2b6263bb: Pushing [================================>                  ]  252.3MB/387.7MB

d57a341501a2: Pushing [=======================>                           ]    140MB/304.2MB

2aad2b6263bb: Pushing [================================>                  ]  254.9MB/387.7MB

d57a341501a2: Pushing [=======================>                           ]  142.7MB/304.2MB

2aad2b6263bb: Pushing [=================================>                 ]  257.6MB/387.7MB

d57a341501a2: Pushing [=======================>                           ]  145.5MB/304.2MB

2aad2b6263bb: Pushing [=================================>                 ]  260.3MB/387.7MB

d57a341501a2: Pushing [========================>                          ]  147.7MB/304.2MB

2aad2b6263bb: Pushing [==================================>                ]  264.1MB/387.7MB

d57a341501a2: Pushing [========================>                          ]  149.9MB/304.2MB

2aad2b6263bb: Pushing [==================================>                ]  267.9MB/387.7MB

d57a341501a2: Pushing [========================>                          ]  152.1MB/304.2MB

2aad2b6263bb: Pushing [===================================>               ]  271.7MB/387.7MB

d57a341501a2: Pushing [=========================>                         ]  154.2MB/304.2MB

2aad2b6263bb: Pushing [===================================>               ]  275.4MB/387.7MB

d57a341501a2: Pushing [=========================>                         ]  156.9MB/304.2MB

2aad2b6263bb: Pushing [====================================>              ]  279.2MB/387.7MB

d57a341501a2: Pushing [==========================>                        ]  159.7MB/304.2MB

2aad2b6263bb: Pushing [====================================>              ]  282.9MB/387.7MB

d57a341501a2: Pushing [==========================>                        ]    163MB/304.2MB

2aad2b6263bb: Pushing [====================================>              ]  286.7MB/387.7MB

d57a341501a2: Pushing [===========================>                       ]  166.4MB/304.2MB

2aad2b6263bb: Pushing [=====================================>             ]  290.5MB/387.7MB

d57a341501a2: Pushing [===========================>                       ]  169.7MB/304.2MB

2aad2b6263bb: Pushing [=====================================>             ]  293.7MB/387.7MB

d57a341501a2: Pushing [============================>                      ]  172.5MB/304.2MB

2aad2b6263bb: Pushing [======================================>            ]  297.5MB/387.7MB

d57a341501a2: Pushing [============================>                      ]  175.3MB/304.2MB

2aad2b6263bb: Pushing [======================================>            ]  301.3MB/387.7MB

d57a341501a2: Pushing [=============================>                     ]    178MB/304.2MB

2aad2b6263bb: Pushing [=======================================>           ]    305MB/387.7MB

d57a341501a2: Pushing [=============================>                     ]  180.2MB/304.2MB

2aad2b6263bb: Pushing [=======================================>           ]  308.8MB/387.7MB

d57a341501a2: Pushing [==============================>                    ]  182.9MB/304.2MB

2aad2b6263bb: Pushing [========================================>          ]  312.6MB/387.7MB

d57a341501a2: Pushing [==============================>                    ]  185.1MB/304.2MB

2aad2b6263bb: Pushing [========================================>          ]  316.4MB/387.7MB

d57a341501a2: Pushing [==============================>                    ]  187.3MB/304.2MB

2aad2b6263bb: Pushing [=========================================>         ]  320.2MB/387.7MB

d57a341501a2: Pushing [===============================>                   ]  189.5MB/304.2MB

2aad2b6263bb: Pushing [=========================================>         ]  323.9MB/387.7MB

d57a341501a2: Pushing [===============================>                   ]  192.2MB/304.2MB

2aad2b6263bb: Pushing [==========================================>        ]  327.7MB/387.7MB

d57a341501a2: Pushing [===============================>                   ]  194.4MB/304.2MB

2aad2b6263bb: Pushing [==========================================>        ]  331.5MB/387.7MB

d57a341501a2: Pushing [================================>                  ]  196.6MB/304.2MB

2aad2b6263bb: Pushing [===========================================>       ]  335.2MB/387.7MB

d57a341501a2: Pushing [================================>                  ]  198.7MB/304.2MB

2aad2b6263bb: Pushing [===========================================>       ]  338.9MB/387.7MB

d57a341501a2: Pushing [=================================>                 ]  201.4MB/304.2MB

2aad2b6263bb: Pushing [============================================>      ]  341.6MB/387.7MB

d57a341501a2: Pushing [=================================>                 ]  204.2MB/304.2MB

2aad2b6263bb: Pushing [============================================>      ]  344.8MB/387.7MB

d57a341501a2: Pushing [==================================>                ]  206.9MB/304.2MB

2aad2b6263bb: Pushing [============================================>      ]    348MB/387.7MB

d57a341501a2: Pushing [==================================>                ]  209.6MB/304.2MB

2aad2b6263bb: Pushing [=============================================>     ]  351.8MB/387.7MB

d57a341501a2: Pushing [==================================>                ]  212.3MB/304.2MB

2aad2b6263bb: Pushing [=============================================>     ]  355.5MB/387.7MB

d57a341501a2: Pushing [===================================>               ]  215.5MB/304.2MB

2aad2b6263bb: Pushing [==============================================>    ]  359.3MB/387.7MB

d57a341501a2: Pushing [===================================>               ]  218.7MB/304.2MB

2aad2b6263bb: Pushing [==============================================>    ]  363.1MB/387.7MB

d57a341501a2: Pushing [====================================>              ]  221.4MB/304.2MB

2aad2b6263bb: Pushing [===============================================>   ]  366.3MB/387.7MB

d57a341501a2: Pushing [====================================>              ]  224.1MB/304.2MB

2aad2b6263bb: Pushing [===============================================>   ]    370MB/387.7MB

d57a341501a2: Pushing [=====================================>             ]  226.8MB/304.2MB

2aad2b6263bb: Pushing [================================================>  ]  373.8MB/387.7MB

d57a341501a2: Pushing [=====================================>             ]  229.5MB/304.2MB

2aad2b6263bb: Pushing [================================================>  ]    377MB/387.7MB

d57a341501a2: Pushing [======================================>            ]  232.2MB/304.2MB

2aad2b6263bb: Pushing [=================================================> ]  380.2MB/387.7MB

d57a341501a2: Pushing [======================================>            ]  234.8MB/304.2MB

2aad2b6263bb: Pushing [=================================================> ]  383.5MB/387.7MB

2aad2b6263bb: Pushing [=================================================> ]  386.7MB/387.7MB

d57a341501a2: Pushing [=======================================>           ]  237.6MB/304.2MB

2aad2b6263bb: Pushing [==================================================>]  389.9MB

d57a341501a2: Pushing [=======================================>           ]  240.2MB/304.2MB

2aad2b6263bb: Pushing [==================================================>]  393.7MB

d57a341501a2: Pushing [=======================================>           ]  242.4MB/304.2MB

2aad2b6263bb: Pushing [==================================================>]    397MB

d57a341501a2: Pushing [========================================>          ]  245.1MB/304.2MB

2aad2b6263bb: Pushing [==================================================>]  398.2MB

d57a341501a2: Pushing [========================================>          ]  247.8MB/304.2MB

d57a341501a2: Pushing [=========================================>         ]    251MB/304.2MB

d57a341501a2: Pushing [=========================================>         ]  254.3MB/304.2MB

d57a341501a2: Pushing [==========================================>        ]  257.5MB/304.2MB

d57a341501a2: Pushing [==========================================>        ]  260.2MB/304.2MB

d57a341501a2: Pushing [===========================================>       ]  262.9MB/304.2MB

d57a341501a2: Pushing [===========================================>       ]  265.6MB/304.2MB

d57a341501a2: Pushing [============================================>      ]  268.3MB/304.2MB

d57a341501a2: Pushing [============================================>      ]  271.5MB/304.2MB

d57a341501a2: Pushing [=============================================>     ]  274.2MB/304.2MB

d57a341501a2: Pushing [=============================================>     ]  276.9MB/304.2MB

d57a341501a2: Pushing [=============================================>     ]  279.6MB/304.2MB

d57a341501a2: Pushing [==============================================>    ]  282.2MB/304.2MB

d57a341501a2: Pushing [==============================================>    ]    285MB/304.2MB

d57a341501a2: Pushing [===============================================>   ]  287.6MB/304.2MB

d57a341501a2: Pushing [===============================================>   ]  290.3MB/304.2MB

2aad2b6263bb: Pushed 

d57a341501a2: Pushing [================================================>  ]  294.6MB/304.2MB

d57a341501a2: Pushing [=================================================> ]    300MB/304.2MB

d57a341501a2: Pushing [=================================================> ]  303.2MB/304.2MB

d57a341501a2: Pushing [==================================================>]    307MB

d57a341501a2: Pushing [==================================================>]  310.9MB

d57a341501a2: Pushing [==================================================>]  314.9MB

d57a341501a2: Pushed 
generateorderpdffunction-91d99985b67f-generate-order-pdf: digest: sha256:16e8121ba342eef1d5395afdea5459f10fc17b7b3aa56de7cc141b7a1d052e33 size: 2833
	Uploading to deb909cc2ea8ca2e585427d42adfa10c  1069 / 1069  (100.00%)
	Uploading to 888f9cc4228f555889a881dbc88a8101  1541 / 1541  (100.00%)
	Uploading to b190722525932bd2ed9a6de452c11f12  1322 / 1322  (100.00%)
	Uploading to c1853ad533ff581dda8f3f0ea485caa4  2689 / 2689  (100.00%)
	Uploading to 4300b939c297c9bf01ac6f2f5d722481  3444 / 3444  (100.00%)
	Uploading to b52a15dc59f8adc6ba67fc4d46559583  2821 / 2821  (100.00%)
	Deploying with following values
	===============================
	Stack name                   : h-dcn
	Region                       : eu-west-1
	Confirm changeset            : False
	Disable rollback             : False
	Deployment image repository  : 
                                       {
                                           "GenerateOrderPdfFunction": "506221081911.dkr.ecr.eu-west-1.amazonaws.com/hdcn6143bf32/generateorderpdffunction42805cd9repo"
                                       }
	Deployment s3 bucket         : aws-sam-cli-managed-default-samclisourcebucket-blif0fm8tjah
	Capabilities                 : ["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM"]
	Parameter overrides          : {"Environment": "prod", "Table": "Producten", "Region": "eu-west-1", "MembersTable": "Members", "PaymentsTable": "Payments", "EventsTable": "Events", "MembershipsTable": "Memberships", "CartsTable": "Carts", "OrdersTable": "Orders", "ParametersTable": "Parameters"}
	Signing Profiles             : {}
Initiating deployment
=====================
GenerateOrderPdfFunction has no authentication.
	Uploading to 2738884280a40f8efb9f7e96c29b7b51.template  45000 / 45000  (100.00%)
Waiting for changeset to be created..
CloudFormation stack changeset
-------------------------------------------------------------------------------------------------
Operation                LogicalResourceId        ResourceType             Replacement            
-------------------------------------------------------------------------------------------------
+ Add                    AuthLayer877c901229      AWS::Lambda::LayerVers   N/A                    
                                                  ion                                             
+ Add                    GenerateOrderPdfFuncti   AWS::Lambda::Permissio   N/A                    
                         onGenerateOrderPdfPerm   n                                               
                         issionStage                                                              
+ Add                    GenerateOrderPdfFuncti   AWS::Lambda::Function    N/A                    
                         on                                                                       
+ Add                    MyApiDeployment4c882eb   AWS::ApiGateway::Deplo   N/A                    
                         1d4                      yment                                           
+ Add                    PdfGeneratorRole         AWS::IAM::Role           N/A                    
* Modify                 ClearCartFunction        AWS::Lambda::Function    False                  
* Modify                 CognitoAdminRole         AWS::IAM::Role           False                  
* Modify                 CognitoCustomMessageFu   AWS::Lambda::Function    False                  
                         nction                                                                   
* Modify                 CognitoCustomMessagePe   AWS::Lambda::Permissio   True                   
                         rmission                 n                                               
* Modify                 CognitoLambdaRole        AWS::IAM::Role           False                  
* Modify                 CognitoPostAuthenticat   AWS::Lambda::Function    False                  
                         ionFunction                                                              
* Modify                 CognitoPostAuthenticat   AWS::Lambda::Permissio   True                   
                         ionPermission            n                                               
* Modify                 CognitoPostConfirmatio   AWS::Lambda::Function    False                  
                         nFunction                                                                
* Modify                 CognitoPostConfirmatio   AWS::Lambda::Permissio   True                   
                         nPermission              n                                               
* Modify                 CognitoPreSignUpFuncti   AWS::Lambda::Function    False                  
                         on                                                                       
* Modify                 CognitoPreSignUpPermis   AWS::Lambda::Permissio   True                   
                         sion                     n                                               
* Modify                 CreateCartFunction       AWS::Lambda::Function    False                  
* Modify                 CreateEventFunction      AWS::Lambda::Function    False                  
* Modify                 CreateMemberFunction     AWS::Lambda::Function    False                  
* Modify                 CreateMembershipFuncti   AWS::Lambda::Function    False                  
                         on                                                                       
* Modify                 CreateOrderFunction      AWS::Lambda::Function    False                  
* Modify                 CreatePaymentFunction    AWS::Lambda::Function    False                  
* Modify                 DeleteEventFunction      AWS::Lambda::Function    False                  
* Modify                 DeleteMemberFunction     AWS::Lambda::Function    False                  
* Modify                 DeleteMembershipFuncti   AWS::Lambda::Function    False                  
                         on                                                                       
* Modify                 DeletePaymentFunction    AWS::Lambda::Function    False                  
* Modify                 DeleteProductFunction    AWS::Lambda::Function    False                  
* Modify                 DynamoDBRole             AWS::IAM::Role           False                  
* Modify                 EmailTemplatesBucket     AWS::S3::Bucket          False                  
* Modify                 ExportMembersFunction    AWS::Lambda::Function    False                  
* Modify                 GetCartFunction          AWS::Lambda::Function    False                  
* Modify                 GetCustomerOrdersFunct   AWS::Lambda::Function    False                  
                         ion                                                                      
* Modify                 GetEventByIdFunction     AWS::Lambda::Function    False                  
* Modify                 GetEventsFunction        AWS::Lambda::Function    False                  
* Modify                 GetMemberByIdFunction    AWS::Lambda::Function    False                  
* Modify                 GetMemberPaymentsFunct   AWS::Lambda::Function    False                  
                         ion                                                                      
* Modify                 GetMemberSelfFunction    AWS::Lambda::Function    False                  
* Modify                 GetMembersFilteredFunc   AWS::Lambda::Function    False                  
                         tion                                                                     
* Modify                 GetMembersFunction       AWS::Lambda::Function    False                  
* Modify                 GetMembershipByIdFunct   AWS::Lambda::Function    False                  
                         ion                                                                      
* Modify                 GetMembershipsFunction   AWS::Lambda::Function    False                  
* Modify                 GetOrderByIdFunction     AWS::Lambda::Function    False                  
* Modify                 GetOrdersFunction        AWS::Lambda::Function    False                  
* Modify                 GetPaymentByIdFunction   AWS::Lambda::Function    False                  
* Modify                 GetPaymentsFunction      AWS::Lambda::Function    False                  
* Modify                 GetProductByIdFunction   AWS::Lambda::Function    False                  
* Modify                 HdcnCognitoAdminFuncti   AWS::Lambda::Function    False                  
                         on                                                                       
* Modify                 InsertProductFunction    AWS::Lambda::Function    False                  
* Modify                 MyApiStage               AWS::ApiGateway::Stage   False                  
* Modify                 MyApi                    AWS::ApiGateway::RestA   False                  
                                                  pi                                              
* Modify                 S3FileManagerFunctionR   AWS::IAM::Role           False                  
                         ole                                                                      
* Modify                 S3FileManagerFunction    AWS::Lambda::Function    False                  
* Modify                 UpdateCartItemsFunctio   AWS::Lambda::Function    False                  
                         n                                                                        
* Modify                 UpdateEventFunction      AWS::Lambda::Function    False                  
* Modify                 UpdateMemberFunction     AWS::Lambda::Function    False                  
* Modify                 UpdateMembershipFuncti   AWS::Lambda::Function    False                  
                         on                                                                       
* Modify                 UpdateOrderStatusFunct   AWS::Lambda::Function    False                  
                         ion                                                                      
* Modify                 UpdatePaymentFunction    AWS::Lambda::Function    False                  
* Modify                 UpdateProductFunction    AWS::Lambda::Function    False                  
* Modify                 scanProductFunction      AWS::Lambda::Function    False                  
- Delete                 AdminGroup               AWS::Cognito::UserPool   N/A                    
                                                  Group                                           
- Delete                 AuthLayerdf1afea14f      AWS::Lambda::LayerVers   N/A                    
                                                  ion                                             
- Delete                 CartsTableResource       AWS::DynamoDB::Table     N/A                    
- Delete                 CognitoMigrationLambda   AWS::IAM::Role           N/A                    
                         Role                                                                     
- Delete                 CognitoUserMigrationFu   AWS::Lambda::Function    N/A                    
                         nction                                                                   
- Delete                 CognitoUserMigrationPe   AWS::Lambda::Permissio   N/A                    
                         rmission                 n                                               
- Delete                 CognitoUserPoolClient    AWS::Cognito::UserPool   N/A                    
                                                  Client                                          
- Delete                 CognitoUserPoolDomain    AWS::Cognito::UserPool   N/A                    
                                                  Domain                                          
- Delete                 CognitoUserPool          AWS::Cognito::UserPool   N/A                    
- Delete                 EventsTableResource      AWS::DynamoDB::Table     N/A                    
- Delete                 GoogleIdentityProvider   AWS::Cognito::UserPool   N/A                    
                                                  IdentityProvider                                
- Delete                 HdcnDashboard            AWS::CloudWatch::Dashb   N/A                    
                                                  oard                                            
- Delete                 HdcnDataBucket           AWS::S3::Bucket          N/A                    
- Delete                 HdcnLedenGroup           AWS::Cognito::UserPool   N/A                    
                                                  Group                                           
- Delete                 LambdaErrorAlertsTopic   AWS::SNS::Topic          N/A                    
- Delete                 LambdaErrorsAlarm        AWS::CloudWatch::Alarm   N/A                    
- Delete                 MembersTableResource     AWS::DynamoDB::Table     N/A                    
- Delete                 MembershipsTableResour   AWS::DynamoDB::Table     N/A                    
                         ce                                                                       
- Delete                 MyApiDeployment3945aa3   AWS::ApiGateway::Deplo   N/A                    
                         ea8                      yment                                           
- Delete                 OrdersTableResource      AWS::DynamoDB::Table     N/A                    
- Delete                 PaymentsTableResource    AWS::DynamoDB::Table     N/A                    
- Delete                 ProductenTable           AWS::DynamoDB::Table     N/A                    
-------------------------------------------------------------------------------------------------
Changeset created successfully. arn:aws:cloudformation:eu-west-1:506221081911:changeSet/samcli-deploy1780238616/d0db3eb5-8b62-4df0-a4ba-5b027983c0e1
2026-05-31 14:44:10 - Waiting for stack create/update to complete
CloudFormation events from stack operations (refresh every 5.0 seconds)
-------------------------------------------------------------------------------------------------
ResourceStatus           ResourceType             LogicalResourceId        ResourceStatusReason   
-------------------------------------------------------------------------------------------------
UPDATE_IN_PROGRESS       AWS::CloudFormation::S   h-dcn                    User Initiated         
                         tack                                                                     
CREATE_IN_PROGRESS       AWS::Lambda::LayerVers   AuthLayer877c901229      -                      
                         ion                                                                      
CREATE_IN_PROGRESS       AWS::IAM::Role           PdfGeneratorRole         -                      
UPDATE_IN_PROGRESS       AWS::IAM::Role           S3FileManagerFunctionR   -                      
                                                  ole                                             
UPDATE_IN_PROGRESS       AWS::IAM::Role           CognitoAdminRole         -                      
UPDATE_IN_PROGRESS       AWS::IAM::Role           DynamoDBRole             -                      
UPDATE_IN_PROGRESS       AWS::S3::Bucket          EmailTemplatesBucket     -                      
CREATE_IN_PROGRESS       AWS::IAM::Role           PdfGeneratorRole         Resource creation      
                                                                           Initiated              
CREATE_IN_PROGRESS       AWS::Lambda::LayerVers   AuthLayer877c901229      Resource creation      
                         ion                                               Initiated              
CREATE_COMPLETE          AWS::Lambda::LayerVers   AuthLayer877c901229      -                      
                         ion                                                                      
UPDATE_COMPLETE          AWS::IAM::Role           CognitoAdminRole         -                      
UPDATE_COMPLETE          AWS::IAM::Role           S3FileManagerFunctionR   -                      
                                                  ole                                             
UPDATE_COMPLETE          AWS::IAM::Role           DynamoDBRole             -                      
CREATE_COMPLETE          AWS::IAM::Role           PdfGeneratorRole         -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    HdcnCognitoAdminFuncti   -                      
                                                  on                                              
CREATE_IN_PROGRESS       AWS::Lambda::Function    GenerateOrderPdfFuncti   -                      
                                                  on                                              
UPDATE_IN_PROGRESS       AWS::Lambda::Function    GetMembersFunction       -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    GetOrdersFunction        -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    DeletePaymentFunction    -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    UpdateProductFunction    -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    GetPaymentsFunction      -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    UpdateMembershipFuncti   -                      
                                                  on                                              
UPDATE_IN_PROGRESS       AWS::Lambda::Function    ClearCartFunction        -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    GetMemberByIdFunction    -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    CreateOrderFunction      -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    UpdateMemberFunction     -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    InsertProductFunction    -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    DeleteProductFunction    -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    CreateCartFunction       -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    UpdateEventFunction      -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    GetEventsFunction        -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    GetPaymentByIdFunction   -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    GetMembershipByIdFunct   -                      
                                                  ion                                             
UPDATE_IN_PROGRESS       AWS::Lambda::Function    GetMembersFilteredFunc   -                      
                                                  tion                                            
UPDATE_IN_PROGRESS       AWS::Lambda::Function    CreateEventFunction      -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    S3FileManagerFunction    -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    GetOrderByIdFunction     -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    CreateMemberFunction     -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    UpdatePaymentFunction    -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    scanProductFunction      -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    UpdateOrderStatusFunct   -                      
                                                  ion                                             
UPDATE_IN_PROGRESS       AWS::Lambda::Function    GetMemberSelfFunction    -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    GetMembershipsFunction   -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    CreateMembershipFuncti   -                      
                                                  on                                              
UPDATE_IN_PROGRESS       AWS::Lambda::Function    CreatePaymentFunction    -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    DeleteMemberFunction     -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    GetCartFunction          -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    DeleteMembershipFuncti   -                      
                                                  on                                              
UPDATE_IN_PROGRESS       AWS::Lambda::Function    GetMemberPaymentsFunct   -                      
                                                  ion                                             
UPDATE_IN_PROGRESS       AWS::Lambda::Function    GetProductByIdFunction   -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    GetEventByIdFunction     -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    GetCustomerOrdersFunct   -                      
                                                  ion                                             
UPDATE_IN_PROGRESS       AWS::Lambda::Function    UpdateCartItemsFunctio   -                      
                                                  n                                               
UPDATE_IN_PROGRESS       AWS::Lambda::Function    DeleteEventFunction      -                      
UPDATE_IN_PROGRESS       AWS::Lambda::Function    ExportMembersFunction    -                      
CREATE_IN_PROGRESS       AWS::Lambda::Function    GenerateOrderPdfFuncti   Resource creation      
                                                  on                       Initiated              
UPDATE_COMPLETE          AWS::S3::Bucket          EmailTemplatesBucket     -                      
UPDATE_IN_PROGRESS       AWS::IAM::Role           CognitoLambdaRole        -                      
UPDATE_COMPLETE          AWS::Lambda::Function    HdcnCognitoAdminFuncti   -                      
                                                  on                                              
UPDATE_COMPLETE          AWS::Lambda::Function    DeletePaymentFunction    -                      
UPDATE_COMPLETE          AWS::Lambda::Function    CreateOrderFunction      -                      
UPDATE_COMPLETE          AWS::Lambda::Function    GetMemberByIdFunction    -                      
UPDATE_COMPLETE          AWS::Lambda::Function    CreateMembershipFuncti   -                      
                                                  on                                              
UPDATE_COMPLETE          AWS::Lambda::Function    CreateCartFunction       -                      
UPDATE_COMPLETE          AWS::Lambda::Function    UpdateOrderStatusFunct   -                      
                                                  ion                                             
UPDATE_COMPLETE          AWS::Lambda::Function    GetEventsFunction        -                      
UPDATE_COMPLETE          AWS::Lambda::Function    GetMembershipsFunction   -                      
UPDATE_COMPLETE          AWS::Lambda::Function    GetPaymentByIdFunction   -                      
UPDATE_COMPLETE          AWS::Lambda::Function    GetPaymentsFunction      -                      
UPDATE_COMPLETE          AWS::Lambda::Function    S3FileManagerFunction    -                      
UPDATE_COMPLETE          AWS::Lambda::Function    GetMembersFunction       -                      
UPDATE_COMPLETE          AWS::Lambda::Function    UpdateMembershipFuncti   -                      
                                                  on                                              
UPDATE_COMPLETE          AWS::Lambda::Function    UpdateProductFunction    -                      
UPDATE_COMPLETE          AWS::Lambda::Function    CreateEventFunction      -                      
UPDATE_COMPLETE          AWS::Lambda::Function    GetCartFunction          -                      
UPDATE_COMPLETE          AWS::Lambda::Function    DeleteProductFunction    -                      
UPDATE_COMPLETE          AWS::Lambda::Function    GetMemberPaymentsFunct   -                      
                                                  ion                                             
UPDATE_COMPLETE          AWS::Lambda::Function    ClearCartFunction        -                      
UPDATE_COMPLETE          AWS::Lambda::Function    InsertProductFunction    -                      
UPDATE_COMPLETE          AWS::Lambda::Function    UpdateMemberFunction     -                      
UPDATE_COMPLETE          AWS::Lambda::Function    GetOrdersFunction        -                      
UPDATE_COMPLETE          AWS::Lambda::Function    UpdatePaymentFunction    -                      
UPDATE_COMPLETE          AWS::Lambda::Function    GetEventByIdFunction     -                      
UPDATE_COMPLETE          AWS::Lambda::Function    scanProductFunction      -                      
UPDATE_COMPLETE          AWS::Lambda::Function    DeleteMemberFunction     -                      
UPDATE_COMPLETE          AWS::Lambda::Function    CreateMemberFunction     -                      
UPDATE_COMPLETE          AWS::Lambda::Function    GetOrderByIdFunction     -                      
UPDATE_COMPLETE          AWS::Lambda::Function    UpdateEventFunction      -                      
UPDATE_COMPLETE          AWS::Lambda::Function    UpdateCartItemsFunctio   -                      
                                                  n                                               
UPDATE_COMPLETE          AWS::Lambda::Function    GetMembershipByIdFunct   -                      
                                                  ion                                             
CREATE_COMPLETE          AWS::Lambda::Function    GenerateOrderPdfFuncti   -                      
                                                  on                                              
UPDATE_COMPLETE          AWS::Lambda::Function    DeleteEventFunction      -                      
UPDATE_COMPLETE          AWS::Lambda::Function    GetMemberSelfFunction    -                      
UPDATE_COMPLETE          AWS::Lambda::Function    GetCustomerOrdersFunct   -                      
                                                  ion                                             
UPDATE_COMPLETE          AWS::Lambda::Function    CreatePaymentFunction    -                      
UPDATE_COMPLETE          AWS::Lambda::Function    ExportMembersFunction    -                      
UPDATE_COMPLETE          AWS::Lambda::Function    GetProductByIdFunction   -                      
UPDATE_COMPLETE          AWS::Lambda::Function    DeleteMembershipFuncti   -                      
                                                  on                                              
UPDATE_COMPLETE          AWS::Lambda::Function    GetMembersFilteredFunc   -                      
                                                  tion                                            
UPDATE_COMPLETE          AWS::IAM::Role           CognitoLambdaRole        -                      
UPDATE_IN_PROGRESS       AWS::ApiGateway::RestA   MyApi                    -                      
                         pi                                                                       
UPDATE_IN_PROGRESS       AWS::Lambda::Function    CognitoPostAuthenticat   -                      
                                                  ionFunction                                     
UPDATE_IN_PROGRESS       AWS::Lambda::Function    CognitoCustomMessageFu   -                      
                                                  nction                                          
UPDATE_IN_PROGRESS       AWS::Lambda::Function    CognitoPreSignUpFuncti   -                      
                                                  on                                              
UPDATE_IN_PROGRESS       AWS::Lambda::Function    CognitoPostConfirmatio   -                      
                                                  nFunction                                       
UPDATE_COMPLETE          AWS::ApiGateway::RestA   MyApi                    -                      
                         pi                                                                       
CREATE_IN_PROGRESS       AWS::Lambda::Permissio   GenerateOrderPdfFuncti   -                      
                         n                        onGenerateOrderPdfPerm                          
                                                  issionStage                                     
CREATE_IN_PROGRESS       AWS::ApiGateway::Deplo   MyApiDeployment4c882eb   -                      
                         yment                    1d4                                             
CREATE_IN_PROGRESS       AWS::Lambda::Permissio   GenerateOrderPdfFuncti   Resource creation      
                         n                        onGenerateOrderPdfPerm   Initiated              
                                                  issionStage                                     
CREATE_COMPLETE          AWS::Lambda::Permissio   GenerateOrderPdfFuncti   -                      
                         n                        onGenerateOrderPdfPerm                          
                                                  issionStage                                     
CREATE_IN_PROGRESS       AWS::ApiGateway::Deplo   MyApiDeployment4c882eb   Resource creation      
                         yment                    1d4                      Initiated              
CREATE_COMPLETE          AWS::ApiGateway::Deplo   MyApiDeployment4c882eb   -                      
                         yment                    1d4                                             
UPDATE_IN_PROGRESS       AWS::ApiGateway::Stage   MyApiStage               -                      
UPDATE_COMPLETE          AWS::ApiGateway::Stage   MyApiStage               -                      
UPDATE_COMPLETE          AWS::Lambda::Function    CognitoCustomMessageFu   -                      
                                                  nction                                          
UPDATE_COMPLETE          AWS::Lambda::Function    CognitoPostAuthenticat   -                      
                                                  ionFunction                                     
UPDATE_COMPLETE          AWS::Lambda::Function    CognitoPreSignUpFuncti   -                      
                                                  on                                              
UPDATE_COMPLETE          AWS::Lambda::Function    CognitoPostConfirmatio   -                      
                                                  nFunction                                       
UPDATE_IN_PROGRESS       AWS::Lambda::Permissio   CognitoCustomMessagePe   Requested update       
                         n                        rmission                 requires the creation  
                                                                           of a new physical      
                                                                           resource; hence        
                                                                           creating one.          
UPDATE_IN_PROGRESS       AWS::Lambda::Permissio   CognitoPostAuthenticat   Requested update       
                         n                        ionPermission            requires the creation  
                                                                           of a new physical      
                                                                           resource; hence        
                                                                           creating one.          
UPDATE_IN_PROGRESS       AWS::Lambda::Permissio   CognitoPreSignUpPermis   Requested update       
                         n                        sion                     requires the creation  
                                                                           of a new physical      
                                                                           resource; hence        
                                                                           creating one.          
UPDATE_IN_PROGRESS       AWS::Lambda::Permissio   CognitoCustomMessagePe   Resource creation      
                         n                        rmission                 Initiated              
UPDATE_IN_PROGRESS       AWS::Lambda::Permissio   CognitoPostConfirmatio   Requested update       
                         n                        nPermission              requires the creation  
                                                                           of a new physical      
                                                                           resource; hence        
                                                                           creating one.          
UPDATE_IN_PROGRESS       AWS::Lambda::Permissio   CognitoPreSignUpPermis   Resource creation      
                         n                        sion                     Initiated              
UPDATE_IN_PROGRESS       AWS::Lambda::Permissio   CognitoPostAuthenticat   Resource creation      
                         n                        ionPermission            Initiated              
UPDATE_COMPLETE          AWS::Lambda::Permissio   CognitoCustomMessagePe   -                      
                         n                        rmission                                        
UPDATE_COMPLETE          AWS::Lambda::Permissio   CognitoPreSignUpPermis   -                      
                         n                        sion                                            
UPDATE_COMPLETE          AWS::Lambda::Permissio   CognitoPostAuthenticat   -                      
                         n                        ionPermission                                   
UPDATE_IN_PROGRESS       AWS::Lambda::Permissio   CognitoPostConfirmatio   Resource creation      
                         n                        nPermission              Initiated              
UPDATE_COMPLETE          AWS::Lambda::Permissio   CognitoPostConfirmatio   -                      
                         n                        nPermission                                     
UPDATE_COMPLETE_CLEANU   AWS::CloudFormation::S   h-dcn                    -                      
P_IN_PROGRESS            tack                                                                     
DELETE_IN_PROGRESS       AWS::DynamoDB::Table     MembersTableResource     -                      
DELETE_IN_PROGRESS       AWS::Cognito::UserPool   CognitoUserPoolClient    -                      
                         Client                                                                   
DELETE_IN_PROGRESS       AWS::CloudWatch::Dashb   HdcnDashboard            -                      
                         oard                                                                     
DELETE_IN_PROGRESS       AWS::Cognito::UserPool   CognitoUserPoolDomain    -                      
                         Domain                                                                   
DELETE_IN_PROGRESS       AWS::DynamoDB::Table     MembershipsTableResour   -                      
                                                  ce                                              
DELETE_IN_PROGRESS       AWS::DynamoDB::Table     ProductenTable           -                      
DELETE_IN_PROGRESS       AWS::DynamoDB::Table     OrdersTableResource      -                      
DELETE_IN_PROGRESS       AWS::CloudWatch::Alarm   LambdaErrorsAlarm        -                      
DELETE_IN_PROGRESS       AWS::DynamoDB::Table     PaymentsTableResource    -                      
DELETE_IN_PROGRESS       AWS::Lambda::Permissio   CognitoUserMigrationPe   -                      
                         n                        rmission                                        
DELETE_IN_PROGRESS       AWS::ApiGateway::Deplo   MyApiDeployment3945aa3   -                      
                         yment                    ea8                                             
DELETE_IN_PROGRESS       AWS::Lambda::Permissio   CognitoPreSignUpPermis   -                      
                         n                        sion                                            
DELETE_IN_PROGRESS       AWS::Lambda::Permissio   CognitoPostConfirmatio   -                      
                         n                        nPermission                                     
DELETE_IN_PROGRESS       AWS::DynamoDB::Table     CartsTableResource       -                      
DELETE_IN_PROGRESS       AWS::Lambda::Permissio   CognitoCustomMessagePe   -                      
                         n                        rmission                                        
DELETE_IN_PROGRESS       AWS::DynamoDB::Table     EventsTableResource      -                      
DELETE_IN_PROGRESS       AWS::Cognito::UserPool   AdminGroup               -                      
                         Group                                                                    
DELETE_IN_PROGRESS       AWS::Cognito::UserPool   HdcnLedenGroup           -                      
                         Group                                                                    
DELETE_IN_PROGRESS       AWS::Lambda::Permissio   CognitoPostAuthenticat   -                      
                         n                        ionPermission                                   
DELETE_SKIPPED           AWS::Lambda::LayerVers   AuthLayerdf1afea14f      -                      
                         ion                                                                      
DELETE_COMPLETE          AWS::Lambda::Permissio   CognitoPreSignUpPermis   -                      
                         n                        sion                                            
DELETE_SKIPPED           AWS::S3::Bucket          HdcnDataBucket           -                      
DELETE_COMPLETE          AWS::Lambda::Permissio   CognitoPostConfirmatio   -                      
                         n                        nPermission                                     
DELETE_COMPLETE          AWS::Lambda::Permissio   CognitoUserMigrationPe   -                      
                         n                        rmission                                        
DELETE_COMPLETE          AWS::Lambda::Permissio   CognitoCustomMessagePe   -                      
                         n                        rmission                                        
DELETE_COMPLETE          AWS::CloudWatch::Alarm   LambdaErrorsAlarm        -                      
DELETE_COMPLETE          AWS::Cognito::UserPool   CognitoUserPoolClient    -                      
                         Client                                                                   
DELETE_COMPLETE          AWS::Lambda::Permissio   CognitoPostAuthenticat   -                      
                         n                        ionPermission                                   
DELETE_COMPLETE          AWS::ApiGateway::Deplo   MyApiDeployment3945aa3   -                      
                         yment                    ea8                                             
DELETE_IN_PROGRESS       AWS::Lambda::Function    CognitoUserMigrationFu   -                      
                                                  nction                                          
DELETE_IN_PROGRESS       AWS::Cognito::UserPool   GoogleIdentityProvider   -                      
                         IdentityProvider                                                         
DELETE_IN_PROGRESS       AWS::SNS::Topic          LambdaErrorAlertsTopic   -                      
DELETE_COMPLETE          AWS::Cognito::UserPool   GoogleIdentityProvider   -                      
                         IdentityProvider                                                         
DELETE_COMPLETE          AWS::CloudWatch::Dashb   HdcnDashboard            -                      
                         oard                                                                     
DELETE_COMPLETE          AWS::Lambda::Function    CognitoUserMigrationFu   -                      
                                                  nction                                          
DELETE_IN_PROGRESS       AWS::IAM::Role           CognitoMigrationLambda   -                      
                                                  Role                                            
DELETE_COMPLETE          AWS::DynamoDB::Table     ProductenTable           -                      
DELETE_COMPLETE          AWS::DynamoDB::Table     PaymentsTableResource    -                      
DELETE_COMPLETE          AWS::DynamoDB::Table     OrdersTableResource      -                      
DELETE_COMPLETE          AWS::DynamoDB::Table     EventsTableResource      -                      
DELETE_COMPLETE          AWS::DynamoDB::Table     CartsTableResource       -                      
DELETE_COMPLETE          AWS::DynamoDB::Table     MembersTableResource     -                      
DELETE_COMPLETE          AWS::DynamoDB::Table     MembershipsTableResour   -                      
                                                  ce                                              
DELETE_COMPLETE          AWS::IAM::Role           CognitoMigrationLambda   -                      
                                                  Role                                            
DELETE_COMPLETE          AWS::Cognito::UserPool   AdminGroup               -                      
                         Group                                                                    
DELETE_COMPLETE          AWS::Cognito::UserPool   HdcnLedenGroup           -                      
                         Group                                                                    
DELETE_COMPLETE          AWS::Cognito::UserPool   CognitoUserPoolDomain    -                      
                         Domain                                                                   
DELETE_IN_PROGRESS       AWS::Cognito::UserPool   CognitoUserPool          -                      
DELETE_COMPLETE          AWS::Cognito::UserPool   CognitoUserPool          -                      
DELETE_COMPLETE          AWS::SNS::Topic          LambdaErrorAlertsTopic   -                      
UPDATE_COMPLETE          AWS::CloudFormation::S   h-dcn                    -                      
                         tack                                                                     
-------------------------------------------------------------------------------------------------
CloudFormation outputs from deployed stack
-------------------------------------------------------------------------------------------------
Outputs                                                                                         
-------------------------------------------------------------------------------------------------
Key                 HDCNBasicMemberRole                                                         
Description         Basic H-DCN member role group name (existing)                               
Value               hdcnLeden                                                                   
Key                 ApiBaseUrl                                                                  
Description         API Gateway endpoint URL                                                    
Value               https://44sw408alh.execute-api.eu-west-1.amazonaws.com/prod                 
Key                 CognitoUserPoolClientId                                                     
Description         Cognito User Pool Client ID for H-DCN Web Application                       
Value               6unl8mg5tbv5r727vc39d847vn                                                  
Key                 CognitoUserPoolId                                                           
Description         Cognito User Pool ID for H-DCN Authentication                               
Value               eu-west-1_OAT3oPCIm                                                         
Key                 AnalyticsDataInfo                                                           
Description         Analytics data is stored in my-hdcn-bucket under analytics/ folder          
Value               s3://my-hdcn-bucket/analytics/                                              
Key                 CognitoUserPoolDomain                                                       
Description         Cognito User Pool Domain for hosted UI                                      
Value               https://h-dcn-auth-new-344561557829.auth.eu-west-1.amazoncognito.com        
-------------------------------------------------------------------------------------------------
Successfully created/updated stack - h-dcn in eu-west-1
