var game={
	data:[],// 启动后是一个二维数组，存储每个方格里的数字
	RN:4,// 总行数
	CN:4,// 总列数
	// 一，游戏启动
	score:0,
	gameover:1,
	keep:0,
	start:function(){ // 游戏启动时调用
		// 1. 初始化一个总行数为RN，总列数为CN的二维数组，每个元素值都为0
		// // this 关键词 谁调用，就指向谁！
		//初始化keep值
		this.keep=0;
		for(var r=0;r<this.RN;r++){
			this.data[r]=[]; // 向二维数组中，追加一个行空数组
			for(var c=0;c<this.CN;c++){
				this.data[r][c]=0;// 初始化二维数组中的每个元素值为0
			}
		}
//		console.log(this);
		/*
			[
				[0,0,0,0],
				[0,0,0,0],
				[0,0,0,0],
				[0,0,0,0]
			]
		*/
		this.randomNum();
		this.randomNum();
		this.updateView();
		console.log(this.data.join("\n")); 
		// 2. 随机位置，产生随机的2或4 - randomNum

	},
	// 二、随机产生数字
	randomNum:function(){
		// 随机产生数字的函数，只有在格子不满员的情况下，才能发生
		// 先判断二维数组中的数据是否满员
		if(!this.isGameOver()){
			console.log("false");
			while(true){
			var r = parseInt(Math.random()*this.RN);
			var c = parseInt(Math.random()*this.CN);
			if(this.data[r][c]==0){
				this.data[r][c] = Math.random()<0.8?2:4;
				break;
				}
		
			}
		}
	},
	// 三、判断游戏是否结束
	//isFull:function(){
	isGameOver:function(){
		for(var r=0;r<this.data.length;r++){
			for(var c=0;c<this.data[r].length;c++){
				if(this.data[r][c]==0){
						return false;
				}
				if(c<3){
					if(this.data[r][c]==this.data[r][c+1]){
						return false;
					}
				}
				if(r<3){
					if(this.data[r][c]==this.data[r+1][c]){
						return false;
					}
				}
			}
			
		}
		return true;
	},
	//渲染更新
	updateView:function(){
		for(var r=0;r<this.data.length;r++){
			for(var c=0;c<this.data[r].length;c++){
				var div=document.getElementById("c"+r+c);
				if(this.data[r][c]!=0){
						div.innerHTML=this.data[r][c];
						div.className="cell n"+this.data[r][c];
				}else{
					div.className="cell";
					div.innerHTML="";
				}
				
			
			}
		}
		//修改标题分数
		document.getElementById("score1").innerHTML=this.score;
		if(this.keep==this.gameover){
			//显示gameover时的分数及覆盖页面
			document.getElementById("gameover").style.display="block";
			document.getElementById("score2").innerHTML=this.score;
		}else{
			document.getElementById("gameover").style.display="none";
		}
	
	},
	//1.左移
	//整体左移
	moveLeft:function(){
		var before=this.data.toString();
		for(var r=0;r<this.data.length;r++){
			this.moveLeftInrow(r);
		}
		var after=this.data.toString();
		if(before!=after){
			console.log("111");
			this.randomNum();
			if(this.isGameOver()){
				this.keep=this.gameover;
				console.log("000000");
			}
			this.updateView();
		}

	},
	//获取右边非0值的下标
	getRightNext:function(r,c){
		for(var next=c+1;next<this.data[r].length;next++){
			if(this.data[r][next]!=0){
				return next;
			}
		}
		return -1;
	},
	//单行左移
	moveLeftInrow:function(r){
		for(var c=0;c<this.data[r].length-1;c++){
			var next=this.getRightNext(r,c);
			if(next==-1){
				break;
			}
			else{
				if(this.data[r][c]==0){
					this.data[r][c]=this.data[r][next];
					this.data[r][next]=0;
					c--;
			}else if(this.data[r][c]==this.data[r][next]){
					this.data[r][c]*=2;
					this.score+=this.data[r][c];
					this.data[r][next]=0;
				}
			}
		}
	},

	//2.右移
	//单行右移
	moveRightInrow:function(r){
		for(var c=this.data[r].length-1;c>0;c--){
			var prev=this.getLeftPrv(r,c);
			if(prev==-1){
				break;
			}
			else{
				if(this.data[r][c]==0){
					this.data[r][c]=this.data[r][prev];
					this.data[r][prev]=0;
					c++;
				}else if(this.data[r][c]==this.data[r][prev]){
					this.data[r][c]*=2;
					this.score+=this.data[r][c];
					this.data[r][prev]=0;
				}	
			}
		}
		
	},
	//获取左侧上一个不为0的下标
	getLeftPrv:function(r,c){
		for(var prev=c-1;prev>=0;prev--){
			if(this.data[r][prev]!=0){return prev}
		}
		return -1;
	},
	//整行右移
	moveRight:function(){
		var before=this.data.toString();
		for(var r=0;r<this.data.length;r++){
			this.moveRightInrow(r);
		}
		var after=this.data.toString();
		if(before!=after){
			this.randomNum();
			if(this.isGameOver()){
				this.keep=this.gameover;
				console.log("000000");
			}
			this.updateView();
		}
	},
	//3.上移
	//整列上移：
	moveUp:function(){
		var before=this.data.toString();
		for(var c=0;c<this.CN;c++){
			this.moveUpIncol(c);
		}
		var after=this.data.toString();
		if(before!=after){
			this.randomNum();
			if(this.isGameOver()){
				this.keep=this.gameover;
				console.log("000000");
			}
			this.updateView();
		}
	},
	//单列上移：
	moveUpIncol:function(c){
		for(var r=0;r<this.data.length-1;r++){
			var down=this.getDownNext(r,c);
			if(down==-1){
				break;
			}else{
				if(this.data[r][c]==0){
					console.log("6666");
					this.data[r][c]=this.data[down][c];
					this.data[down][c]=0;
					r--;
				}else if(this.data[r][c]==this.data[down][c]){
					console.log("budengyu");
					this.data[r][c]*=2;
					this.score+=this.data[r][c];
					this.data[down][c]=0;
				}
			}
		}
	},
	//获取当前列下一个不为0的下标：
	getDownNext:function(r,c){
		for(var down=r+1;down<this.data.length;down++){
			if(this.data[down][c]!=0){
				return down;
			}
		}
		return -1;
	},
	//4.下移
	//整体下移：
	moveDown:function(){
		var before=this.data.toString();
		for(var c=0;c<this.CN;c++){
			this.moveDownIncol(c);
		}
		var after=this.data.toString();
		if(before!=after){
			this.randomNum();
			if(this.isGameOver()){
				this.keep=this.gameover;
				console.log("000000");
			}
			this.updateView();
		}

	},
	//单列下移：
	moveDownIncol:function(c){
	for(var r=this.data.length-1;r>0;r--){
		var up=this.getUpPrev(r,c);
		if(up==-1){break;}
		else{
			if(this.data[r][c]==0){
				this.data[r][c]=this.data[up][c];
				this.data[up][c]=0;
				r++;
			}else if(this.data[r][c]==this.data[up][c]){
				this.data[r][c]*=2;
				this.score+=this.data[r][c];
				this.data[up][c]=0;
			}
		}
	}
	},
	getUpPrev:function(r,c){
		for(var up=r-1;up>=0;up--){
			if(this.data[up][c]!=0){
				return up;
			}
		}
		return -1;
	}
}
//重置游戏
function restart(){
	game.start();
}

window.onload=function(){
	game.start(); 
	document.onkeydown=function(){
		var e=window.event||argument[0];
		if(e.keyCode==37){
			game.moveLeft();
		}else if(e.keyCode==39){
			game.moveRight();
		}else if(e.keyCode==38){
			game.moveUp();
		}else if(e.keyCode==40){
			game.moveDown();
		}

	}
}