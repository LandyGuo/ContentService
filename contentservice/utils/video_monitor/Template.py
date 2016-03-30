#coding=utf8
HTML_ROW_UNIT = r'<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'

HTML_CONTENT = '''
                    <html>
                    <body>
                    <p>近期爬虫库运行总体情况如下：</p>
                    <table border="1">
                    <tr>
                      <th>资源总数</th>
                      <th>更新数</th>
                      <th>新增数</th>
                      <th>严重错误数</th>
                      <th>统计日期</th>
                    </tr>
                    {%for item in item_list%}
                    {{item|safe}} 
                    {% endfor %}
                    </table>
                    <p>统计图如下所示：</p>
                    <img  src="cid:image1"/>
                    </body>
                    <p>详情请见附件</p>
                    </html>
                '''