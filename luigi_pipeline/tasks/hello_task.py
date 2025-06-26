import luigi

class HelloTask(luigi.Task):
    def run(self):
        with self.output().open('w') as f:
            f.write('Hello Luigi!')
    
    def output(self):
        return luigi.LocalTarget('/tmp/hello.txt')