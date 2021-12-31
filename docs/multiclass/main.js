/*variables*/
var model;
var canvas;
var classNames = [];
var canvas;
var coords = [];

$(function() {
    canvas = document.getElementById('canvas');
})

/*set the table of the predictions */
function setTable(top3, probs) {
    //loop over the predictions 
    for (var i = 0; i < top3.length; i++) {
        let sym = document.getElementById('sym' + (i + 1))
        let prob = document.getElementById('prob' + (i + 1))
        sym.innerHTML = top3[i]
        prob.innerHTML = Math.round(probs[i] * 100 * 100) / 100
    }
    //create the pie 
    createPie(".pieID.legend", ".pieID.pie");
}

/*get the current image data */
function getImageData() {
        const imgData = canvas.getContext("2d").getImageData(0,0,400,400);
        return imgData
    }

/*get the prediction*/
function getFrame() {
        //get the image data from the canvas 
        const imgData = getImageData()
        //get the prediction 
        const pred = model.predict(preprocess(imgData)).dataSync()
        //find the top 3 predictions 
        const indices = findIndicesOfMax(pred, 3)
        const probs = findTopValues(pred, 3)
        const names = getClassNames(indices)
        //set the table 
        setTable(names, probs)
}

/*get the the class names */
function getClassNames(indices) {
    var outp = []
    for (var i = 0; i < indices.length; i++)
        outp[i] = classNames[indices[i]]
    return outp
}

/*load the class names */
async function loadDict() {
    loc = 'model/class_names.txt'
    await $.ajax({
        url: loc,
        dataType: 'text',
    }).done(success);
}

function success(data) {
    const lst = data.split(/\n/)
    for (var i = 0; i < lst.length - 1; i++) {
        let symbol = lst[i]
        classNames[i] = symbol
    }
}

/*get indices of the top probs*/
function findIndicesOfMax(inp, count) {
    var outp = [];
    for (var i = 0; i < inp.length; i++) {
        outp.push(i); // add index to output array
        if (outp.length > count) {
            outp.sort(function(a, b) {
                return inp[b] - inp[a];
            }); // descending sort the output array
            outp.pop(); // remove the last index (index of smallest element in output array)
        }
    }
    return outp;
}

/*find the top 3 predictions*/
function findTopValues(inp, count) {
    var outp = [];
    let indices = findIndicesOfMax(inp, count)
    // show 3 greatest scores
    for (var i = 0; i < indices.length; i++)
        outp[i] = inp[indices[i]]
    return outp
}

/*preprocess the data*/
function preprocess(imgData) {
    return tf.tidy(() => {
        //convert to a tensor 
        let tensor = tf.browser.fromPixels(imgData, numChannels = 3)
        console.log(tensor)
        //resize 
        const resized = tf.image.resizeBilinear(tensor, [400, 400]).toFloat()
        //We add a dimension to get a batch shape 
        const batched = resized.expandDims(0)
        return batched
    })
}

/*load the model*/
async function start() {
    //load the model 
    model = await tf.loadGraphModel('model/model.json')
    document.getElementById('status').innerHTML = 'Model Loaded';
    //load the class names
    await loadDict()
    //Enable upload
    imageLoader.disabled = false
}

/*Upload image functionality*/
var imageLoader = document.getElementById('imageLoader');
    imageLoader.addEventListener('change', handleImage, false);

function handleImage(e){
    var reader = new FileReader();
    reader.onload = function(event){
        var img = new Image();
        img.onload = function(){
            canvas.getContext('2d').drawImage(img,0,0,400,400);
            getFrame();
        }
        img.src = event.target.result;
    }
    reader.readAsDataURL(e.target.files[0]);
}
