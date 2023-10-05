

# Photographic Processes Identification

This is an ongoing attempt to build a deep learning based tool for identifying [photographic processes](http://www.graphicsatlas.org/identification/) using a digital copy.

You can [**try out**](https://guilhermesfc.github.io/ppi/) the current models here:
- A [Binary model](https://guilhermesfc.github.io/ppi/binary) that tries to distinguish between _Salted Paper Print_ and _Albumen Print_. Current accuracy for this model is around 90%.
- A [Multiclass model](https://guilhermesfc.github.io/ppi/multiclass) that tries to predict one of the following processes: _Albumen Print_, _Ambrotype/Tintype/Ferrotype_, _Carbon Print_, _Cyanotpye_, _Daguerreotpye_, _Silver Developing-out Papers (DOP)_, _Silver Printing-out Papers (POP)_, _Platinotype/Palladiotype_, _Salted Paper Print_. Current accuracy for this model is around 70%.

## Using the source code
The source code for the tool is available trough this repository and you can clone it and change it according to the license.

### Collecting and preparing the data
The repository contains
 - A general configuration file: ```config.yaml```
 - A web crawler that retrieves metadata from publicly available image sites and stores it into a local database: ```image_metadata_crawler.py```
 - A module to download images to disk: ```image_downloader.py```
 - A module to standardize the description of photographic processes: ```medium_mapper.py```
 - A module to interact with a SQLite database: ```database.py```

You can find an example on how to use these modules in this notebook: [Fetch and prepare image data](fetch_prepare_data.ipynb)

Note: make sure you only crawl websites for which you have permissions to do so! 

### Training the models
After data is available and cropped as expected, you need to copy it into google drive and execute the following colab notebooks for generating the models:
- [Binary Classification](https://drive.google.com/file/d/1F0ZFmtV4gvjmmqHcTY-mdpWVEPyALLp2/view?usp=sharing)
- [Multiclass Classification](https://drive.google.com/file/d/1F0crgmxQ6Nv9gtAYDA8qs66JxvKE0WcW/view?usp=sharing)

You can try running this locally, but unless you have appropriate resources (GPUs), training will be **slow**.
Copies of the notebooks are available in the [colab_noteboks directory](colab_notebooks).

### Deploying the models
The models need to be [converted into TensorFlow.js](https://www.tensorflow.org/js/guide/conversion).

Afterwards, they can be run in the browser. Please see the code under ```docs``` for this, or take a look at this [tutorial](https://medium.com/tensorflow/train-on-google-colab-and-run-on-the-browser-a-case-study-8a45f9b1474e).





