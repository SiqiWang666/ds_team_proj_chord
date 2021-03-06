const $container = $('#container .circle-container');
const $tip = $('#tip');

let fingers;

// $tip.text('Creating Chord ring...');
// $.get('/create_ring/', function (data) {
//     return data
// }).done(function (data) {
//     run()
// })

// run();
const simplemde = new SimpleMDE({
    element: $('#text-area')[0],
});
$('#text').hide()
startRender();

function renderFilelist(data) {
    const list = data.content;
    const textArea = $('#text-area')
    textArea.hide()
    let filelist = '';
    for (let i = 0; i < list.length; i++) {
        filelist += `<div class="f"><a href="#">${list[i]}</a></div>`
    }
    const fileContainer = $('#file-tree');
    fileContainer.html(filelist)

    let filename = '';
    fileContainer.on('click', '.f', (e) => {
        filename = e.currentTarget.innerText
        $.get(`/get_file/?filename=${filename}`, function(data) {
            console.log(data)
            simplemde.value(data.content);
        })
        $('#text').show()
    })

    $('#file').on('click', '#cancel', (e) => {
        $('#text').hide()
    })

    $('#file').on('click', '#save', (e) => {
        const content = simplemde.value();
        const param = {
            content: content,
            filename: filename
        }

        $.get(`/save_file/?${$.param(param)}`, function(data) {
            if (!data.error) {
                $('#tip').html('Save succeeded')
            } else {
                $('#tip').html('Save failed, try again later')
            }
            $('#text').hide()
        })
    })
}

function run() {
    startRender();

    $('#lookup').on('click', (e) => {
        const key = $('#lookup_key').val();
        const onNode = $('#on_node').val();
        if (key == undefined || onNode == undefined) {
            alert('Please input key and node id');
            return
        }

        if (!fingers.shape[onNode]) {
            alert('That slot has no node');
            return
        }
        $.get(`/lookup/?key=${key}&id=${onNode}`, function (data) {
            alert(`Key found at Node ${data.target}`);
        })
    })

    $('#add_node').on('click', (e) => {
        const ip = $('#add_node_ip').val();
        if (!validateIp(ip)) {
            return
        }

        $.get(`/add_node/?ip=${ip}`, (data) => {
            render(data);
            $tip.text(`node ${ip} added`)
        });
    })

    $('#leave_node').on('click', (e) => {
        const id = $('#leave_node_id').val();
        if (!id) {
            alert('Please input the right node id');
        }

        $.get(`/remove_node/?id=${id}`, (data) => {
            render(data);
            $tip.text(`node ${id} leaves`)
        })
    })
}

function render(data) {
    fingers = data;
    const numOfLot = Math.pow(2, data.m || 3);
    const lots = [];
    const shape = fingers.shape

    for(let i = 0; i < numOfLot; i++) {
        const dot = $(`<div ${shape[i] != null ? 'class="active"' : ''} node_id=${i}>
            <span style="color: red">${i}</span>
        </div>`);
        const deg = (360 / numOfLot) * i;
        dot.css('transform', `rotate(${deg}deg) translate(16.5em) rotate(-${deg}deg)`)
        lots.push(dot);
    }

    const nodeInfo = $('#node_info');

    $container.on('mouseover', '.active', (e) => {
        const current = $(e.target).attr('node_id');
        const info = fingers.shape[current];

        let fingerTable = info.finger.reduce((prev, cur) => {
            prev.push(`
                <span>start: ${cur.start}</span>
                <span>node: ${cur.node}</span>
                </br>
            `);
            return prev;
        }, []);

        let node = `<div>
            <p>ID: ${current}</p>
            <p>Address ${JSON.parse(info.addr).join(':')}</p>
            <p>Finger Table:</p>
            <p>${fingerTable.join('')}</p>
        </div>`;

        nodeInfo.html(node);
    })

    $container.on('mouseout', '.active', (e) => {
        nodeInfo.html('Hover on a node to view details');
    })

    $container.html(lots)
}

function renderFingerTable(finger, ip) {
    const lines = [];

    for (let i = 0; i < finger.length; i++) {
        let line = `<div>start: ${finger[i].start}, node: ${finger[i].node}</div>`
        lines.push(line)
    }

    return `<div><b>Finger table of ${ip}</b>:  ${lines.join('')}</div>`
}

function renderGraph(data) {
    data = data.shape
    // data.finger = JSON.parse
    if (data.length == 0) {
        return
    }

    const myChart = echarts.init($('#container')[0]);

    const formatted = [];
    var edges = [];

    for (let i = 0; i < data.length; i++) {
        // ugly due to unknown python list not searializable
        data[i].finger = eval(data[i].finger)

        formatted.push({
            id: data[i].id,
            tooltip: renderFingerTable(data[i].finger, data[i].ip),
            name: data[i].id,
        })

        const succID = data[i].successor;

        for (let j = 0; j < data.length; j++) {
            if (succID == data[j].id) {
                edges.push({
                    source: i,
                    target: j
                });

                // console.log(edges)
            }
        }
    }

    myChart.setOption({
        tooltip: {},
        series: [{
            symbolSize: 20,
            edgeSymbol: ['arrow'],
            force: {
                repulsion: 1000,
                edgeLength: 100,
            },
            type: 'graph',
            layout: 'force',
            roam: true,
            label: {
                normal: {
                    show: true
                }
            },
            tooltip: {
                show: true,
            },
            // data: data,
            data: formatted,
            links: edges,
            lineStyle: {
                normal: {
                    opacity: 0.9,
                    width: 2,
                    curveness: 0.2,
                    type: 'dotted',
                }
            }
        }]
    });

    // console.log('nodes: ' + data.length);
    // console.log('links: ' + data.length);
}

function validateIp(ipaddress) {
    if (/^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/.test(ipaddress)) {
        return (true)
    }
    alert("You have entered an invalid IP address!")
    return (false)
}

function startRender() {
    setInterval(() => {
        $.get('/get_all_finger/', function (data) {
            $tip.text('');
            // render(data);

            renderGraph(data)
        })
    }, 1000)
    $.get('/list_dir/', function (data) {
        $tip.text('');

        renderFilelist(data)
    })
}