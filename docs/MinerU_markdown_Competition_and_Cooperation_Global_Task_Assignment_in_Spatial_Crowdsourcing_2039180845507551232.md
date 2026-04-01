# Competition and Cooperation: Global Task Assignment in Spatial Crowdsourcing

Boyang Li , Yurong Cheng , Member, IEEE, Ye Yuan , Member, IEEE, Changsheng Li , Member, IEEE, Qianqian Jin, and Guoren Wang 

Abstract—Online spatial crowdsourcing platforms provide popular O2O services in people’s daily. Users submit real-time tasks through the Internet and require the platform to immediately assign workers to serve them. However, the imbalance distribution of tasks and workers leads to the rejection of some tasks, which reduces the profit of the platform. In this paper, we propose that similar platforms can form an alliance to make full use of the global service supply through cooperation. We name the problem as Global Task Assignment (GTA), in which platforms are allowed to hire idle workers from other platforms to improve the profit of all the platforms together. Different from relevant works, the decisionmakers in GTA are platforms rather than individual workers, which can better assign workers in all platforms and improve the overall profit. We design an auction-based incentive mechanism (AIM), to motivate platforms to rent idle workers to other platforms so that increase their own profit. Based on the mechanism, we propose a greedy-based assignment algorithm (BaseGTA), in which platforms greedily maximizes their current profit. We further propose a prediction-based assignment algorithm (ImpGTA), in which platforms make decisions based on the spatial-temporal distribution in the future time. Experimental results show that platforms using our algorithms can achieve higher profit than the existing studies. 

Index Terms—Auction, crowdsroucing, incentive mechanism, spatial databases, task assignment. 

# I. INTRODUCTION

W ITH the development of smart phones and GPS technol-ogy, online spatial crowdsourcing platforms are more ogy, online spatial crowdsourcing platforms are more and more popular in people’s daily life [1], [2]. In these platforms, such as DiDi1 and Uber,2 users can submit real-time tasks with a payment at any time, and ask the platform to immediately assign crowdsourcing workers to serve them. The above process are defined as the task assignment problem [3]. 

Manuscript received 28 June 2022; revised 22 December 2022; accepted 21 February 2023. Date of publication 2 March 2023; date of current version 15 September 2023. The work of Boyang Li was supported in part by the NSFC under Grant 62202046 and in part by the China Postdoctoral Science General Program Foundation under Grant 2018M631358. The work of Yurong Cheng was supported by the NSFC under Grants 61902023 and U21B2007. The work of Ye Yuan was supported by the NSFC under Grant 61932004, 62225203, and U21A20516. The work of Guoren Wang was supported by the NSFC under Grants 61732003 and U2001211. Recommended for acceptance by Y. Tong. (Corresponding author: Yurong Cheng.) 

The authors are with the School of Computer Science and Technology, Beijing Institute of Technology, Beijing 100811, China (e-mail: liboyang@bit.edu.cn; yrcheng@bit.edu.cn; yuan-ye@bit.edu.cn; lcs@bit.edu.cn; 1176002998@qq.com; wanggr@bit.edu.cn). 

Digital Object Identifier 10.1109/TKDE.2023.3251443 

1https://www.didiglobal.com/ 

2https://www.uber.com/ 


TABLE I THE ARRIVAL TIME OF WORKERS AND TASKS


<table><tr><td>τ1</td><td>τ2</td><td>τ3</td><td>τ4</td><td>τ5</td><td>τ6</td><td>τ7</td><td>τ8</td><td>τ9</td><td>τ10</td></tr><tr><td>t4</td><td>w1</td><td>w2</td><td>w3</td><td>w4</td><td>t1</td><td>t2</td><td>t6</td><td>t5</td><td>t3</td></tr></table>

Existing studies on task assignment usually focus on a single platform. These studies either aim at maximizing the number of assigned results [4], [5], [6], or minimizing the service cost [7], [8]. However, due to the non-uniform spatial distribution of tasks and workers, some tasks may be rejected since the workers nearby are all busy. Thus, some users are not serviced and are unsatisfied, which reduces the profit of the platforms and the sanctification of users. With more and more platforms providing similar services, there may be workers from other platforms nearby when users can not be served by one platform. Therefore, users can choose other platforms for service. However, it is inconvenient to switching among different platforms one by one. Consequently, a new task assignment model, Cross Online Matching (COM), was proposed [9]. It allows platforms to temporarily hire workers from other platforms if their workers nearby are not enough to serve the users. Users can be served only by submitting tasks to one platform without considering constantly switching platforms. In traditional task assignment, there is a competitive relationship among platforms. Now, platforms have found that the way of competition has reached the bottleneck, and it is difficult for platforms to obtain a better market. Therefore, they have accepted the COM model. Similar service has been adopted by DiDi1, AMAP3, Baidu $\mathrm { M a p } ^ { 4 }$ and so on. However, they only focus on task collection and ignore the optimization of task assignment. 

In COM, the platforms share an idle worker list. Suppose that a task $t$ with reward $v$ is submitted to platform $p$ . If there are no workers of $p$ (called inner workers) can serve t, $p$ will send a hiring request with an estimated payment $r$ to the nearby workers of other platforms (called outer workers). Outer workers who are willing to serve $t$ will response to the request and $t$ will be assigned to one of them. When $t$ is finished, the outer worker will receive the payment $r$ , and the profit of $p$ is $v - r$ . 

Example 1. Fig. 1 and Table I show an example with 6 tasks $\left( t _ { 1 } \right.$ to $t _ { 6 , }$ ), 4 workers $\stackrel { \cdot } { w } _ { 1 }$ to $w _ { 4 }$ ) from 4 platforms $\textcircled { p _ { 1 } }$ to $p _ { 4 } .$ ). $w _ { 1 }$ , $t _ { 1 }$ and $t _ { 2 }$ belong to $p _ { 1 }$ . $w _ { 2 }$ and $t _ { 4 }$ belong to $p _ { 2 } . \ w _ { 3 }$ , $t _ { 3 }$ and 

3https://www.amap.com/ 

4https://map.baidu.com/ 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/3e7511e15185ea99784e09d0ad19e4ca0a87147414645933b6bfaa157bd84deb.jpg)



(a) Results of TOTA


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/90166935f16159706c9999cb5a5c9c541267e6aa04814805b0a4b8296cd9e3ce.jpg)



(b) Results of COM



Fig. 1. Example of online matching results.


$t _ { 6 }$ belong to $p _ { 3 } . \ w _ { 4 }$ and $t _ { 5 }$ belong to $p _ { 4 }$ . Each task needs to be assigned to workers immediately after it is submitted. Workers can only serve tasks later than they arrive. The dashed circles are the service radius of workers, which means a worker only serve the tasks located in the dashed circle. The number in parentheses is the reward of the tasks. Red number is the payment to the workers. If we adopt the solution on single platforms (TOTA) [5], only $t _ { 1 }$ , $t _ { 5 }$ and $t _ { 6 }$ can be served by inner workers as shown in Fig. 1(a). The profit of $p _ { 1 }$ is 8 by serving $t _ { 1 }$ . The profit of $p _ { 3 }$ is 8 by serving $t _ { 6 }$ . The profit of $p _ { 4 }$ is 5 by serving $t _ { 5 }$ . The profit of $p _ { 2 }$ is 0. Thus, the total profit is $8 + 8 + 5 = 2 1$ . But in COM, more tasks can be served by hiring outer workers. The result is shown in 1(b). $w _ { 1 }$ still serves $t _ { 1 }$ . $t _ { 2 }$ is served by $w _ { 3 }$ and $p _ { 1 }$ needs to pay $w _ { 3 }$ the payment 10. Thus, the profit of $p _ { 1 }$ is $8 + ( 1 3 - 1 0 ) = 1 1$ . $w _ { 2 }$ serves $t _ { 6 }$ and receives the payment 7 from $p _ { 3 }$ . Thus, the profit of $p _ { 2 }$ is 7. $p _ { 3 }$ receives the payment from $t _ { 2 }$ and $t _ { 6 }$ , and needs to pay $w _ { 2 }$ for 7. Thus, the profit of $p _ { 3 }$ is $1 0 + ( 8 - 7 ) = 1 1$ . $w _ { 4 }$ serves $t _ { 5 }$ and the profit of $p _ { 4 }$ is 5. Thus, the total profit is $1 1 + 7 + 1 1 + 5 = 3 4 { \cdot }$ . 

Obviously, COM can improve the profit of all the platforms. However, It still faces the following limitations: 

- Limitation1 (L1): COM takes outer workers as individuals and a platform can directly sends the requests to them. In fact, workers are selfish and short-sighted. They determine whether to accept tasks according to their own situation. They do not make decisions from the overall perspective. For example, drivers may serve orders greedily, and miss more valuable orders in the future. It may not fully maximize the profit of themselves and the platforms. 

Limitation2 (L2): All idle workers are shared by all the platforms in COM. Sharing information will expose the supply and demand distribution and the business secrets of the platforms. If information is shared, other platforms may change their own operation strategies according to the distribution of the platforms, thus suppressing other platforms. It is unacceptable to use these information for malicious business competition in real applications. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/51857db0e046634a04ce76d5b5bcd4d3ef8df18b065c401225ad5345839e4026.jpg)



Fig. 2. Workflow of GTA.


In this paper, we propose a variant of COM, named Global Task Assignment (GTA). To overcome L1, it is the platforms to decide whether rent workers or not. Platforms can use strategies to maximize the overall profit. To overcome L2, the key information (such as distribution of workers) is managed by their own platforms, which are no longer shared among platforms. The workflow of GTA is shown in Fig. 2. When a platform (inner platform) decides to not serve a task, it sends the task information to other platforms (outer platforms) in Step 1 and 2. The reward of the task is unknown to outer platforms. We design an auction-based incentive mechanism while making decisions of outer platforms. In the mechanism, outer platforms are called service sellers. They send the bidding price to the inner platform according to the distribution of their own workers and tasks in Step 3 and 4. The bidding price is the lower bound of the payment they can approve. The inner platform is regarded as the service buyer. The buyer will select a winner in the sellers and determine a critical payment to the winner. The inner platform notifies the user and winner in Step 5. Finally, the winner dispatch a worker to serve the task and earn the critical payment in Step 6. 

In summary, our contributions are as following: 

- We propose Global Task Assignment problem (GTA) in online spatial crowdsourcing platforms. GTA builds an alliance consisting of multiple platforms, the relationship between platforms has changed from competition to 

cooperation, and the profit is improved by making full use of the service supply. 

- We design an auction-based incentive mechanism, named AIM. AIM is proved as an awesome auction model. The payment is easier to be accepted by outer platforms, and malicious bidding is avoided through the restriction among platforms. 

- We propose a greedy-based task assignment algorithm, named BaseGTA, to help platforms improve their current profit. We also propose a prediction-based algorithm, named ImpGTA. ImpGTA considers the temporal and spatial distribution over time and improves the profit from a global perspective. 

- We conduct extensive experiments over real and synthetic datasets. The results prove that our algorithms are more effective than existing studies. 

The rest of the paper is organized as follows. We review related works in Section II. We introduce the basic concepts and formulate the problem in Section III. We introduce and analyze AIM in Section IV. We introduce the task assignment algorithms in Section V. We report the experimental results in Section VI and conclude the paper in Section VII. 

# II. RELATED WORKS

In this section, we review the task assignment algorithms and incentive mechanism in spatial crowdsourcing. 

Task assignment. In task assignment, the platform directly sends tasks to suitable workers according to the constraints, such as travel budget [10], service radius [11], arrival time [12] and so on. In some studies [13], [14], the platform assigns tasks on the premise of knowing the distribution of tasks and workers in advance. These are called offline scenarios. Kazemi et al. [13] proposed the task assignment problem aiming at maximizing the number of tasks. Deng et al. [15] focused on tasks that consists of a set of subtasks. They proposed exact and approximate algorithms for different data scale respectively. Cheng et al. [16] proposed the multi-skill task assignment problem. In their problem, workers are required to have corresponding skills to complete the tasks. Li et al. [17] proposed trichromatic matching problem in which the matching results satisfy the stable constraints. 

On the contrary, some studies [5], [18], [19] only know the distribution before the current time, which are called online scenarios. The problem studied in this paper is also an online scenario. Tong et al. [20] defined the online task assignment problem as online bipartite matching, in which users and workers are two disjoint sets. The goal of the problem is to find a matching result to maximize the total profit of the platform. Xu et al. [21] used a more general linear programming method to represent the online task assignment problem with conflict constraintts. They proofed that the proposed solutions with a theoretical upper bound. Chen et al. [7] proposed a problem aiming at minimizing the maximum waiting time, so as to improve the user satisfaction. [22] and [23] used the prediction algorithms to improve the effectiveness of task assignment. Liu et al. [24] considered that tasks should be completed one by one according to the 

dependency. Zhao et al. [25] studied a problem with fairness and proposed algorithms based on game theory. Costa et al. [26] adopted skyline query to explore the relationship between detour and rewards while serving tasks. Song et al. [27] also studied trichromatic matching in the online scenarios. 

Some studies also pay attention to data protection in task assignment [28], [29], [30]. To et al. [31], [32] proposed a framework to protect the information of both tasks and workers, which satisfied the geo-indistinguishability. Tao et al. [33] proposed a differential privacy method based on HST index. They index the space through HST, map the actual locations to adjacent leaf nodes and dispatch tasks based on the private data. 

Incentive Mechanism. Different from task assignment, some studies focus on design incentive mechanism to motivate workers serving the tasks [34], [35]. The most common incentive mechanism is to give workers monetary reward [36], [37]. Tong et al. [38] proposed a pricing method based on supply and demand to maximize the total utility of task assignment. Tian et al. [39] proposed a movement-based incentive mechanism to encourage workers to go to areas where supply is less than demand to earn more profit. Similarly, Uber uses Surge pricing [40] to realize the balance of supply and demand. Yang et al. [41] studied two kinds of model and proposed the mechanism based on Stackelberg Equilibrium. Wang et al. [37] proposed a distribute mechanism. Users and workers directly send tasks and bidding prices without the centralized platform. The mechanism can maximize the quality of service and satisfies the budget constraints. Zhang et al. [42] proposed the decision-making mechanism for the ride-sharing problem. The platforms receive task quotations from users and workers, and use the double auction model to match users and workers who meet the constraints. Xiao et al. [43] studied route planning problem and proposed a mechanism to maximize social welfare and protect workers’ privacy by using the reverse auction model with the detour cost. Yue et al. [44] combined deep learning and reverse auction mechanism to realize intelligent decision-making incentive scheme through automatic feature selection and deep network. Yang et al. [41] proposed platform-centered and user-centered system models respectively. They designed a decision-making mechanism based on Stackelberg game, and proved that there is a unique Stackelberg Equilibrium to maximize the utility value in this method. 

The aforementioned studies only focus on a single platform, without considering the cooperation. The problem definitions are quite different from ours in this paper. COM [9] is the latest work to consider the cooperation between platforms. But according to the analysis, there are still some limitations. Although some companies already allow users submit tasks to multiple platforms through their apps, the strategies adopted by the real-world services are relatively simple. As the third party, they are only responsible for the data collection and not design algorithms to optimize the service. Thus, we propose GTA to overcome the limitations and maximize the profit of platforms. Different from existing studies and applications, GTA includes both task assignment and incentive mechanism. It is a task assignment process when the platforms decide which worker to serve the task. When an inner platform cannot serve a 


TABLE II SUMMARY OF NOTATIONS


<table><tr><td>Notations</td><td>Description</td></tr><tr><td>W, w</td><td>Worker set and the worker</td></tr><tr><td>τw,1w, radw, uw, pw</td><td>Arrival time, location, service radius, unit price, platform</td></tr><tr><td>T, t</td><td>Task set and the task</td></tr><tr><td>τt, lt, ld, vt, pt</td><td>Create time, source, destination, reward, platform</td></tr><tr><td>P, p</td><td>Platform set, the platform</td></tr><tr><td>dis()</td><td>Distance function</td></tr><tr><td>rij</td><td>Critical payment</td></tr><tr><td>Utj</td><td>Profit contribution</td></tr><tr><td>suij</td><td>Minimum dispatching payment</td></tr><tr><td>B, bi</td><td>Bidding price set, the bidding price of pi</td></tr><tr><td>Δτ</td><td>Future time period</td></tr><tr><td>TpkΔτ</td><td>Predicted task set in Δτ</td></tr><tr><td>Uexp(TpkΔτ)</td><td>Expected task reward in Δτ</td></tr></table>

task, it should use the incentive mechanism to motivate the outer platforms. 

# III. PROBLEM DEFINITION

In this section, we first introduce some basic concepts and then formally define the problem. Important notations are summarized in Table III. 

# A. Problem Definition

We build an alliance consists of $n$ similar crowdsourcing platforms $P = \{ p _ { 1 } , p _ { 2 } , . . . , p _ { n } \}$ . In each platform, users can submit crowdsourcing tasks $t = < \tau _ { t } , \mathbf { l } _ { t } ^ { s } , \mathbf { l } _ { t } ^ { d } , v _ { t } , p _ { t } >$ , where $\tau _ { t }$ is the create time when $t$ is submitted to $p _ { t }$ , $\mathbf { l } _ { t } ^ { s }$ and $\mathbf { l } _ { t } ^ { d }$ are source and destination locations, $v _ { t }$ is the monetary reward of $t$ . The platforms dispatch their workers to finish the tasks. Workers are denoted as $w = < \tau _ { w } , 1 _ { w } , r a d _ { w } , u _ { w } , p _ { w } >$ , where $\tau _ { w }$ is the time that $w$ is ready to serve users, ${ \bf l } _ { w }$ is the location, $r a d _ { w }$ is the service radius, $u _ { w }$ is the minimum unit price of dispatching $w$ to serve tasks belongs to other platforms and $p _ { w }$ is the platform that $w$ works for. An idle worker $w$ can only serve the tasks which satisfy $\tau _ { t } \geq \tau _ { w }$ and $d i s ( \mathbf { l } _ { t } ^ { s } , \mathbf { l } _ { w } ) \leq r a d _ { w }$ , where $d i s ( )$ is the distance between two locations. Workers become idle at $\tau _ { w }$ , and become unavailable during serving tasks. Platforms are required to response to the tasks immediately. If a task cannot be served, it will be rejected and there is no profit. For a platform $p _ { k }$ (inner platform), other platforms are called outer platforms of $p _ { k }$ . Workers work for $p _ { k }$ are called inner workers. Workers work for outer platforms are called outer workers of $p _ { k }$ . 

A task $t _ { j }$ belong to $p _ { k }$ can be served by inner or outer workers. The profit contributed by $t _ { j }$ can be calculated as following. If $t _ { j }$ is rejected, the contribution is 0. If $t _ { j }$ is served by an inner worker, $p _ { k }$ can earn the whole reward $v _ { t _ { j } }$ . If $t _ { j }$ is served by an outer worker $w$ works for $p _ { i }$ , $p _ { k }$ needs to pay $p _ { i }$ the payment of employing $w$ , denoted as $r _ { i j }$ . The profit contribution to $p _ { k }$ is denoted as $\boldsymbol { v } _ { t _ { j } } - \boldsymbol { r } _ { i j }$ . Therefore, the contribution of $t _ { j }$ to the 

profit of $p _ { k }$ is denoted as 

$$
U _ {t _ {j}} = \left\{ \begin{array}{l l} 0 & \text {r e j e c t e d} \\ v _ {t _ {j}} & \text {s e r v e d b y a n i n n e r w o r k e r} \\ v _ {t _ {j}} - r _ {i j} & \text {s e r v e d b y a n o u t e r w o r k e r} \end{array} \right. \tag {1}
$$

In COM, $r _ { i j }$ is an estimated value only according to the history of outer workers. The inner platforms directly send $r _ { i j }$ to outer workers and let them decide to accept it or not. In fact, outer workers often have minimum acceptable payments of different tasks. The employment payment should be related to the actual tasks not just workers’ history. In this problem, outer platforms submit the bidding prices and $r _ { i j }$ is a critical payment determined by the inner platform. The inner platform would like $r _ { i j }$ to be as lower as possible, so that maximizing its own profit. On the contrary, outer platforms would like to earn more profit. They hope $r _ { i j }$ to be as large as possible. Since $p _ { i }$ needs to dispatch $w$ to serve $t _ { j }$ , there is a minimum dispatching payment $s u _ { i j }$ that $p _ { i }$ can accept. Therefore, the range of $r _ { i j }$ should be in $[ s u _ { i j } , v _ { t _ { j } } ]$ , where $s u _ { i j } = u _ { w } \times \left( d i s ( \mathbf { l } _ { t } ^ { s } , \mathbf { l } _ { w } ) + d i s ( \mathbf { l } _ { t } ^ { s } , \mathbf { l } _ { t } ^ { d } ) \right)$ is the minimum dispatching payment of $w$ to arrive the source location and serve the whole task. 

Although outer platforms can earn a higher profit with a higher bidding price, the probability of obtaining the task reduces at the same time. Therefore, they have to make choices between high profit and high possibility of being selected. In order to realize the trade-off, we design an auction-based incentive mechanism in the proposed algorithms. It aims to encourage each outer platform to obtain tasks through trustful bidding. 

Finally, we formally define the Global Task Assignment problem (GTA). 

Definition 1 (GTA). For an alliance with a set of similar spatial crowdsourcing platforms $_ { P }$ , a set of workers $W$ and a set of tasks $_ { \mathbf { \delta T } }$ , the goal of GTA is to find a matching result to maximize the profit of each platform in the alliance, where the following constraints are satisfied: 

- Temporal Constraint: An idle worker $w$ can only serve a task $t$ which satisfies $\tau _ { t } \geq \tau _ { w }$ . 

- Spatial Constraint: An idle worker $w$ can only serve a task $t$ which satisfies $d i s ( \mathbf { l } _ { t } ^ { s } , \mathbf { l } _ { w } ) \leq r a d _ { w }$ . 

- Unique Constraint: An idle worker can only serve one task until the task is finished. 

In both GTA and COM, workers and users appear dynamically, which are online problems [45]. COM needs to solve two issues: select which outer worker to serve the task, and how to pay for the worker. In GTA, we also consider these two issues. Therefore, GTA is a variant of COM, the hardness is also similar with it. As proved in [9], TOTA [5] is a special case of COM when $| P | = 1$ . Therefore, TOTA is also a special case of GTA. The hardness of TOTA has been well-studied and proved to be NP-hard, thus, GTA is also NP-hard. 

To solve GTA, our proposed algorithms have two import parts: the incentive mechanism and the task assignment. The auction-based incentive mechanism encourages the platforms to conduct truthful bidding and guarantees that they receive a critical payment. The task assignment algorithms determine which tasks are severed by inner workers (inner conditions) 

and whether the platforms should participate in the task bidding (outer conditions). 

# IV. INCENTIVE MECHANISM

In this section, we introduce the auction-based incentive mechanism (AIM) and prove that it is an awesome model. 

# A. AIM Algorithm

The first parts of our algorithm is the auction-based incentive mechanism. If a task is sent to outer platforms, the progress is built as an auction. The outer platforms are regarded as service sellers who sell their service supply. They send the bidding price to the inner platform. The inner platform is regarded as the service buyer. It select a suitable outer platform and pay for its service. The mechanism helps outer platforms to decide the bidding price if they want to serve tasks. 

- The outer platforms submit their bidding prices. 

- The inner platform selects a winner. 

- The inner platform decides a payment to the winner. 

In the first step, outer platforms submit the payment that they want to get from the task. The payment is based on the evaluation of the task. Because platforms want to earn profit, the payment must be no less than the dispatching price. In the second step, the inner platform will select the minimum bidding price so that to maximize its own profit. In the last step, the inner platform will determine a critical payment to the winner. The payment should be no less the bidding price of the winner. For outer platforms, a high bidding price will increase the profit but reduce the winning probability. Vice versa. Therefore, outer platforms need to make a trade-off between profit and winning probability. The goal of the incentive mechanism is to help outer platforms find the suitable bidding price and prevent malicious competition. 

Suppose an outer platform $p _ { i }$ with bidding price $b _ { i }$ , a task $v _ { j }$ and the critical payment $r _ { i j }$ , if bidding price $b _ { i }$ is less than $r _ { i j }$ , $p _ { i }$ will be the winner. Otherwise, $p _ { i }$ will lose. Because there is only one winner, the inner platform must select a winner who can achieve the maximal profit. In AIM, the critical payment is the profit that outer platforms earn from the tasks. If the bidding price is less than the critical payment, the platform will be the winner. To design an awesome mechanism, we select the platform with the minimal bidding price as the winner and the second minimal bidding price as the payment to the winner. When determine the payment, we remove $b _ { i }$ from the bidding result, and select a new winner $p _ { l }$ . Then we use $b _ { l }$ as the critical payment $r _ { i j }$ to $p _ { i }$ . To design an awesome incentive mechanism, if the real bidding price is a dominant strategy for each platform according to their own valuation, and the profit of the platforms is not negative, then the auction is said to be Dominant Strategy Incentive Compatible (DSIC). Therefore, in order to ensure that AIM is awesome and implementable, AIM meets following properties: 

- Truthfulness: the mechanism is truthfulness if and only if the best bidding strategy is to use the minimum dispatching price. 

- Individual rationality: The profit of outer platforms is nonnegative. In other words, $r _ { i j }$ is not less than the minimum dispatching price $s u _ { i j }$ . 


Algorithm 1: AIM Algorithm.


Input: Inner platform $p_k$ , Outer Platform Set $P^{out}$ , A task $t_j$ Output: Payment $r_{ij}$ , winner $p_i$ 1: $B = \emptyset$ 2: for each outer platform $p_i \in P^{out}$ do  
3: Submit a bidding price $b_i$ 4: $B = B \cup \{b_i\}$ 5: end for  
6: Select an outer platform $p_i$ with the maximal $U_{t_j}$ as the winner  
7: Select the critical payment $r_{ij}$ with the maximal $U_{t_j}$ in $B \setminus \{b_i\}$ 8: return $r_{ij}, p_i$ 

- Profitability: The profit of inner platform is non-negative. In other words, $r _ { i j }$ is not larger than $v _ { t _ { j } }$ . 

Computational efficiency: The complexity of the mechanism is polynomial time. 

The pseudocode of AIM is shown in Algorithm 1. $p _ { k }$ sends a task to the outer platforms. Each outer platform responds a bidding price if they decide to serve the task. $p _ { k }$ can get a bidding price set $\textbf {  { B } }$ (Lines 1–5). $p _ { k }$ selects an outer platform $p _ { i }$ as the winner with the maximum profit contribution to itself (Line 6). Then, $p _ { k }$ calculate a critical payment $r _ { i j }$ to the winner (Line 7). 

# B. Theoretical Analysis

In this section, we analyze and prove that AIM is awesome. 

Lemma 1. The auction-based incentive mechanism guarantees the truthfulness of the bids submitted by the outer platforms. 

Proof. First, if an outer platform $p _ { i }$ wins with a bidding price $b _ { i }$ , it means that $b _ { i }$ is the minimum value in $_ B$ . So the profit of the inner platform $p _ { k }$ is maximized. If $p _ { i }$ uses a price $b _ { i } ^ { \prime } < b _ { i } , p _ { i }$ is still the winner. The reason is that $b _ { i } ^ { \prime }$ is still the minimum value and will be selected by $p _ { k }$ . Therefore, the incentive mechanism is monotonic. Second, for the payment $r _ { i j }$ , $p _ { i }$ will be the winner if $b _ { i } < r _ { i j }$ . Otherwise, $p _ { i }$ will lose. In fact, $r _ { i j }$ is the minimum value in $_ B$ except $b _ { i }$ and it is a critical payment. According to Myerson’s Lemma [46], the incentive mechanism guarantees the truthfulness. - 

Lemma 2. The auction-based incentive mechanism guarantees individual rationality. 

Proof. If $p _ { i }$ loses, the profit is 0. If $p _ { i }$ wins, $b _ { i }$ is the minimum value in $\textbf {  { B } }$ . The payment $r _ { i j }$ is the second smallest value in $_ B$ . Thus, $r _ { i j } - b _ { i } \geq r _ { i j } - s u _ { i j } \geq 0$ . The incentive mechanism guarantees individual rationality. - 

Lemma 3. The auction-based incentive mechanism guarantees profitability. 

Proof. If $t _ { j }$ is rejected, the profit of $p _ { k }$ is 0. If $p _ { i }$ wins with a bidding price $b _ { i }$ , $b _ { i }$ must be not larger than $v _ { t _ { j } }$ . Because the purpose of $p _ { k }$ is to maximize its own profit, $p _ { k }$ will reject the task if $b _ { i } > v _ { t _ { j } }$ . While calculating the critical payment, the inner platform takes the minimum value between $v _ { t _ { j } }$ and $r _ { i j }$ to ensure 

that $r _ { i j }$ is not larger than $v _ { t _ { j } }$ . Thus, $v _ { t _ { j } } - r _ { i j } \geq 0$ . The incentive mechanism guarantees profitability. - 

Lemma 4. The auction-based incentive mechanism achieves computational efficiency. 

Proof. While selecting an outer worker, the worst case of outer platform $p _ { i }$ to submit a biding price is $O ( | W ^ { p _ { i } } | )$ , where $W ^ { p _ { i } }$ is $p _ { i }$ ’s workers Therefore, the worst case of selecting a winner and determine the payment among all the outer platforms is $O ( | W | )$ . For each platform, it needs to store the information of workers and the space complexity is $O ( | W | )$ . To store the bidding prices, the space complexity is $O ( | P | )$ . The total space complexity is $O ( | W | + | P | )$ . Therefore, the incentive mechanism achieve computational efficiency. - 

Through the analysis, the above prove that AIM meets truthfulness, individual rationality, profitability and computational efficiency. Therefore, it is an awesome auction-based incentive mechanism. 

# V. TASK ASSIGNMENT ALGORITHMS

In this section, we propose two task assignment algorithms. Each algorithm consists of inner and outer conditions to help platforms make decisions. We first introduce the BaseGTA algorithm, which assign tasks in a greedy manner. We further propose the ImpGTA algorithm, which using a temporal window on the future distribution to improve the performance of task assignment. 

# A. BaseGTA Algorithm

Real-time tasks need to be processed immediately, the goal of BaseGTA is to serve each task as possible. Therefore, it adapts the greedy manner. When a task is submitted, the inner platform gives priority to scheduling inner workers to serve it. If there are no idle inner workers, it immediately sends the task to the outer platforms. For outer platforms, they will arrange idle workers to serve any tasks to improve the utilization rate of workers. Therefore, the conditions are as following. In inner and outer conditions, if platforms can serve the tasks, they will dispatch a worker or participate the bidding. 

- Inner/Outer Condition: There is at least an idle worker. 

The pseudocode of BaseGTA is shown in Algorithm 2. For each new arrival task $t _ { j }$ , the inner platform first assigns an inner worker $w$ to $t _ { j }$ (Line 3). Existing task assignment algorithms such as TOTA [5] can be executed in the LocalT askAssign process. If the local assignment successes, $w$ will serve $t _ { j }$ and get the profit $v _ { t _ { j } }$ (Lines 4–7). Otherwise, $p _ { k }$ sends requests to outer platform. Outer platforms that meets the outer conditions will participate in the bidding (Lines 9–13). Through AIM, $p _ { k }$ selects an outer platform $p _ { i }$ as the winner and calculate a payment to the winner. The winner dispatches a worker to serve $t _ { j }$ and get the profit $r _ { i j }$ (Lines 14–15). 

Example 2. Back to Example 1. When $t _ { 4 }$ arrives, it is rejected due to no worker can serve it. When $t _ { 1 }$ arrives, $p _ { 1 }$ dispatches $w _ { 1 }$ to serve it. When $t _ { 2 }$ arrives, $p _ { 1 }$ sends it to the outer platforms because the inner condition is not satisfied. $p _ { 2 }$ , $p _ { 3 }$ and $p _ { 4 }$ participate in the bidding. Suppose the bidding price is $\{ 6 , 7 , 8 \}$ , then $p _ { 2 }$ is selected as the winner and the critical payment is 7. 


Algorithm 2: BaseGTA Algorithm.


Input: Platform set $P$ , Worker set $W$ , Task set $\pmb{T}$ Output: Matching result $M$ 1: Let $M = \emptyset$ 2: for a new arrival task $t_j$ of $p_k$ in $\pmb{T}$ do   
3: $w = LocalTaskAssign(t_j,p_k)$ 4: if $w$ exists then   
5: Add $(w,t_j,v_{t_j})$ into $M$ 6: Continue   
7: end if   
8: for each outer platform $p_i$ do   
9: $w = LocalTaskAssign(t_j,p_i)$ 10: if $w$ exists then   
11: Participate in the bidding   
12: end if   
13: end for   
14: $r_{ij},p_i = AIM(p_k,P\backslash \{p_k\} ,t_j)$ 15: Add $(w,t,r_{ij})$ into $M$ 16: end for   
17: return $M$ 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/3024fd49fa57a0f7837b972107118809fb710da76e8be34bc003109829fa7204.jpg)



Fig. 3. The results of BaseGTA.


When $t _ { 6 }$ arrives, $w _ { 3 }$ serves it because the inner policy is satisfied. Finally, $w _ { 4 }$ is dispatched to serve $t _ { 5 }$ . Thus, the total profit is $( 8 + 6 ) + 7 + 8 + 5 = 3 4$ . The results are shown in Fig. 3. 

Complexity Analysis. When the task is served by an inner worker, the complexity to find a suitable worker is $O ( | W ^ { p _ { k } } | )$ . While selecting an outer worker, the complexity to select a winner and determine the payment is $O ( | W | )$ . The complexity of dispatching an outer worker is $O ( | W ^ { p _ { i } } | )$ . The worst case for all the task is $O ( | T | \times | W | )$ . To store the information of workers and users, the space complexity is $O ( | W | + | T | )$ . Considering the space complexity of AIM, the total space complexity is $O ( | W | + | P | + | T | )$ . 

Although BaseGTA is efficiency, it does not consider the relationship between workers and tasks in the future. Inner workers are likely to be occupied by low-reward tasks and may miss high-reward tasks. For outer platforms, the changes of supply and demand on their own platforms are not taken into 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/e1c08f512ae8e4ea98e3fd8484c638c3a2219099d1afb1440465e2737dd6a836.jpg)



Fig. 4. The results of ImpGTA.


account, so that their workers serve low-value tasks on other platforms and cannot serve their own tasks. Therefore, platforms are likely to lose the opportunity to achieve higher profit if they ignore the difference among tasks. Therefore, we further propose an improved algorithm from the perspective of global spatial-temporal distribution. 

# B. ImpGTA Algorithm

As analyzed above, BaseGTA only focuses on the tasks at the current time, ignores the reward and future distribution of tasks. It is easy to miss high-reward tasks so that reducing the profit of the platforms. Therefore, we further propose an ImpGTA algorithm. The main idea of ImpGTA is to use a temporal window to observe the distribution of tasks and reward within the window, so as to make decisions that whether the inner and outer conditions are satisfied. 

ImpGTA is based on the task distribution predicted through the historical data by [47]. As the prediction algorithms cannot know the actual locations and arrival time, we divide the whole space into several grids, and one day is divided into several time periods. Then, each task belongs to a specific grid and a time period. The input is the historical task data and the output is the number of tasks and the distribution of task reward, denoted as $\tilde { \pmb { T } }$ . The distribution is used to determine what kind of tasks the platform gives priority to. 

Each platform no longer greedily serves all tasks. When a task $t _ { j }$ arrives, the platforms decide whether to dispatch a worker according to the distribution in a future time window $\Delta \tau$ . The length of $\Delta \tau$ is the sum of one or more time periods in the prediction step. Because the platforms know the information of workers who are idle and will finish a task in $\Delta \tau$ , they can estimate a gap between supply and demand. If there are enough workers, a worker $w$ is dispatched to serve $t _ { j }$ . If workers are not enough to complete all tasks, they give priority to tasks with higher profit. Existing study [27] uses a static threshold to filter the tasks. However, the distribution changes over time, the static threshold influences the overall profit. Therefore, we adopt a dynamic threshold according to distribution. 


Algorithm 3: ImpGTA Algorithm.


Input: Platform set $P$ , Worker set $W$ , Task set $\pmb{T}$ Output: Matching result $M$ 1: Let $M = \emptyset$ 2: for a new arrival task $t_j$ of $p_k$ in $\pmb{T}$ do   
3: if $|W^{p_k}| > |\tilde{T}_{\Delta \tau}^{p_k}|$ or $v_{t_j}\geq \mathbb{U}_{exp}(\tilde{T}_{\Delta \tau}^{p_k})$ then   
4: Lines 3-7 of Algorithm2   
5: end if   
6: for each outer platform $p_i$ do   
7: if $|W^{p_i}| > |\tilde{T}_{\Delta \tau}^{p_i}|$ or $su_{ij}\geq \mathbb{U}_{exp}(\tilde{T}_{\Delta \tau}^{p_i})$ then   
8: Lines 9-15 of Algorithm2   
9: end if   
10: end for   
11: end for   
12: return $M$ 

For a platform $p ^ { k }$ , the inner conditions are as following. 

- Inner Conddenoted as $| W ^ { p _ { k } } | > | \tilde { \mathbf { T } } _ { \Delta \tau } ^ { p _ { k } } |$ enough workers to serve tasks,. 

- Inner Condition2: Workers are not enough but $v _ { t _ { j } }$ is larger than the expected task reward, denoted as $v _ { t _ { j } } \geq$ $\mathbb { U } _ { e x p } ( \tilde { \pmb { T } } _ { \Delta \tau } ^ { p _ { k } } ) .$ . 

where $W ^ { p _ { k } }$ is the worker set of p $p _ { k } , \tilde { \pmb { T } } _ { \Delta \tau } ^ { p _ { k } }$ is the predicted task set in $\Delta \tau$ , $\mathbb { U } _ { e x p } ( \tilde { \pmb { T } } _ { \Delta \tau } ^ { p _ { k } } )$ is the expected task reward that $p _ { k }$ can get in the prediction results. 

For the outer platforms, it is also necessary to determine whether to participate in the bidding according to the actual situation. If there are enough workers, they will participate in the bidding to earn more profit. If the payment they can get is larger than the profit on their own tasks, they can also participate in the bidding. The outer conditions are as following. 

- Outer Condition1: There are enough workers to serve tasks, denoted as $| W ^ { p _ { i } } | > | \tilde { \mathbf { T } } _ { \Delta \tau } ^ { p _ { i } } |$ . 

- Outer Condition2: The minimum pathe expected task reward, denoted as $\overline { { s u } } _ { i j } \geq \mathbb { U } _ { e x p } ( \mathbf { \tilde { T } } _ { \Delta \tau } ^ { p _ { i } } )$ 

The pseudocode of our method is shown in Algorithm 3. For each new arrival task $t _ { j }$ , we discuss two cases respectively (Line 2). If the inner conditions are satisfied, the platform $p _ { k }$ dispatches a worker $w$ to serve it and get the profit $v _ { t _ { j } }$ (Lines $3 -$ 5). If $t _ { j }$ cannot be served by inner workers, $p _ { k }$ sends requests to outer platform. Each platform responds a bidding price if the outer conditions are satisfied. $p _ { k }$ can get a bidding price set $_ B$ . $p _ { k }$ selects an outer platform $p _ { i }$ as the winner with the maximum profit contribution to itself and calculate a critical payment to the winner. The winner dispatches a worker to serve $t _ { j }$ and get the profit $r _ { i j }$ (Lines 7–10). 

Example 3. Back to Example 1. Suppose the length of temporal window is 5 time units. $p _ { 1 }$ predicts that there are 2 tasks and the average reward is 10. p2 predicts there is no tasks. $p _ { 3 }$ predicts that there are 2 tasks and the average reward is 12. $p _ { 4 }$ predicts that there is 1 task and the average reward is 3. $t _ { 4 }$ still can not be served. When $t _ { 1 }$ arrives, the inner conditions are not satisfied, and $p _ { 1 }$ sends it to the outer platforms. Only $p _ { 2 }$ and $p _ { 4 }$ can serve $t _ { 1 }$ . Suppose the bidding price of is $\{ 6 , 5 \}$ , then $p _ { 4 }$ wins the bidding with payment 6. When $t _ { 2 }$ arrives, the inner conditions 

are satisfied, and $w _ { 1 }$ serves $t _ { 1 }$ . When $t _ { 6 }$ arrives, $p _ { 3 }$ sends it to outer platforms and only $w _ { 2 }$ can serve it. When $t _ { 5 }$ arrives, there is no worker can serve it. When $t _ { 3 }$ arrives, $p _ { 3 }$ dispatches $w _ { 3 }$ to serve it. Thus, the total profit is $( 2 + 1 3 ) + 7 + ( 1 6 + 1 ) + 6 = 4 5$ . 

Complexity Analysis. Similar with BaseGTA, when the task is served by an inner worker, the complexity to find a suitable worker is $O ( | W ^ { p _ { k } } | )$ , the complexity to select a winner and determine the payment is $O ( | W | )$ . The complexity of dispatching an outer worker is $O ( | W ^ { p _ { i } } | )$ . The worst case for all the task is $O ( | T | \times | W | )$ . The space complexity to storing the prediction results is $O ( | T | )$ . The complexity of storing the information of tasks, platforms and workers is $O ( | T | + | P | + | W | ) _ {  }$ . Therefore, the space complexity is $O ( | W | + | T | + | P | + | T | )$ . 

# VI. EXPERIMENTS

In this section, we conduct experiments over real and synthetic datasets. We report the experimental results and verify the effectiveness, efficiency and scalability. 

# A. Dataset and Setup

The experiments are conducted over two real datasets from Xian and Chengdu (two cities in China) on November 1st [9]. Each dataset consists of 5 popular taxi-calling platforms. There are total 16047 workers and 320981 tasks in Xian, 32401 workers and 556179 tasks in Chengdu. The attributes of tasks include the create time, source and destination locations and the reward. Each worker works for one of the platforms. Their attributes include the arrival time, the location, the radius and the minimum unit dispatching price. The locations are expressed in longitude and latitude. We set $r a d _ { w }$ as $1 . 0 k m$ and $u _ { w }$ as 3.0 per kilometer based on the daily experience and the statistical results. We also generate the synthetic datasets to verify the scalability of varying $\vert W \vert$ , $| T |$ , $r a d _ { w }$ , $u _ { w }$ and $\Delta \tau$ . Based on the real dataset, we generate the datasets by random selecting workers and orders. In this process, we dynamically change one parameter and keep other parameters unchanged. The statistics of the datasets are shown in Table III, the default values are displayed in bold. 

We compare the proposed algorithms (BaseGTA and ImpGTA) with non-cooperative algorithm TOTA [5] and COM algorithms (DemCOM and RamCOM) [9]. We verify the effectiveness and efficiency by the following metrics: 

- Total Profit: the sum of profit of the tasks that are served. 

- Acceptance ratio: the ratio of the number of tasks accepted by the outer platforms to the number of all tasks sent to the outer platforms. 

- Payment ratio: the average proportion of payment to outer workers and reward of the tasks. 

- Response time: the latency between the time when the task is submitted and the time when the assignment result is obtained. 

- Memory cost: the memory cost by the algorithms. 

We set the grid size as $3 . 0 k m$ , the length of time period as 1 minute. The results of RamCOM are the average value with different thresholds. The algorithms are implemented by $\mathrm { C } { + } { + }$ . The experiments are conducted on a machine with Intel Core i5 CPU and 32 GB main memory. 


TABLE III STATISTICS OF DATASETS



(a) Real Datasets


<table><tr><td rowspan="2" colspan="2">Dataset</td><td colspan="5">Platform</td></tr><tr><td>A</td><td>B</td><td>C</td><td>D</td><td>E</td></tr><tr><td rowspan="2">Xian</td><td>|W|</td><td>63877</td><td>64035</td><td>64434</td><td>64504</td><td>64131</td></tr><tr><td>|T|</td><td>3187</td><td>3261</td><td>3195</td><td>3205</td><td>3199</td></tr><tr><td rowspan="2">Chengdu</td><td>|W|</td><td>110741</td><td>110853</td><td>111928</td><td>111693</td><td>110964</td></tr><tr><td>|T|</td><td>6425</td><td>6417</td><td>6447</td><td>6562</td><td>6550</td></tr><tr><td colspan="2">radw(km)</td><td></td><td></td><td>1.0</td><td></td><td></td></tr><tr><td colspan="2">uw</td><td></td><td></td><td>3.0</td><td></td><td></td></tr></table>


(b) Synthetic Datasets


<table><tr><td>Parameter</td><td>Value</td></tr><tr><td>|W|</td><td>1k, 2k, 5k, 8k, 10k</td></tr><tr><td>|T|</td><td>10k, 50k, 100k, 200k, 500k</td></tr><tr><td>radw(km)</td><td>0.5, 1.0, 1.5, 2.0, 2.5</td></tr><tr><td>uw</td><td>2.0, 3.0, 4.0, 5.0, 6.0</td></tr><tr><td>Δτ(min)</td><td>1, 3, 5, 10, 15</td></tr></table>

# B. Results on Real Datasets

In this section, we report the results over real datasets and verify the effectiveness and efficiency of the algorithms. 

Effectiveness w.r.t total profit. As shown in Table IV, we can observe that the total profit of the cooperative algorithms is better than TOTA. ImpGTA is better than the others. It can increase the total profit than TOTA about $6 \times 1 0 ^ { 5 }$ in Xian and $4 . 7 \times 1 0 ^ { 5 }$ in Chengdu. It indicates that the dynamic threshold of ImpGTA is more effective than the static threshold of RamCOM. BaseGTA can improve the total profit than TOTA about $1 . 5 \times 1 0 ^ { 5 }$ in Xian and $2 . 7 \times 1 0 ^ { 5 }$ in Chengdu. To further analyze the effectiveness of the algorithms, we report the profit of each platform in Fig. 5, ImpGTA can achieve the highest profit improvement in most platforms. BaseGTA can achieve good results in some of platforms, which is related to the temporal and spatial distribution. In general, ImpGTA can achieve the best results and prove the effectiveness of our algorithm. 

Efficiency w.r.t Response Time and Memory Cost. We report the average response time of each task and the memory cost to verify the efficiency. The results are shown in Table IV. BaseGTA is the fastest. The response time of all algorithms is in milliseconds. For an online spatial crowdsourcing platform, the millisecond delay is completely acceptable, and users will not be dissatisfied. As for the memroy cost, ImpGTA uses more memory than other algorithms. The reason is that it requires additional space to store the prediction results. Other algorithms only need to store the information of workers and tasks, so the memory cost are similar. Both the increase of response time and memory cost is acceptable. Therefore, the results prove that our algorithm is efficient. 

# C. Results on Synthetic Datasets

In this section, we use the synthetic datasets to verify the scalability of the algorithms. 


TABLE IV RESULTS ON REAL DATASETS


<table><tr><td rowspan="2"></td><td rowspan="2">Dataset</td><td colspan="5">Algorithm</td></tr><tr><td>TOTA</td><td>DemCOM</td><td>RamCOM</td><td>BaseGTA</td><td>ImpGTA</td></tr><tr><td rowspan="3">Xian</td><td>Profit(×106)</td><td>5.98</td><td>6.19</td><td>6.28</td><td>6.15</td><td>6.57</td></tr><tr><td>Response Time(ms)</td><td>0.39</td><td>0.42</td><td>0.51</td><td>0.36</td><td>0.63</td></tr><tr><td>Memory Cost(MB)</td><td>36.62</td><td>40.05</td><td>40.25</td><td>40.09</td><td>52.78</td></tr><tr><td rowspan="3">Chengdu</td><td>Profit(×106)</td><td>11.04</td><td>11.20</td><td>11.40</td><td>11.31</td><td>11.51</td></tr><tr><td>Response Time(ms)</td><td>0.45</td><td>0.53</td><td>2.16</td><td>0.44</td><td>1.51</td></tr><tr><td>Memory Cost(MB)</td><td>59.13</td><td>60.13</td><td>59.22</td><td>60.12</td><td>81.01</td></tr></table>


The bold values are the best results in the experiments,so we show them in bold. 


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/05a5d8a1d5c05b9557d604412b62421ca1d183b174372b869b978e5b960017df.jpg)



(a) Profit of Each Platform on Xian Dateset


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/0767fbdc4bcf23e337a14bbfc9b3b4edea8648f077e7783701f6e8beb7f3b025.jpg)



(b) Profit of Each Platform on Chengdu Dataset



Fig. 5. Profit of Each Platform on Real Datasets.


Total Profit w.r.t $\vert W \vert$ . We change $| W |$ from $1 \mathrm { ~ k ~ }$ to $1 0 \mathrm { k }$ and the total profit is shown in Fig. 6(a). With the increase of $| W |$ , more tasks can be served leading to the increase of profit in all the algorithms. The results of GTA algorithms are better than COM algorithms and TOTA. ImpGTA can achieve the highest profit because it can handle the supply-demand relationship more reasonably through the temporal window. BaseGTA does not filter the high reward tasks, which makes many workers occupied by low reward tasks when workers are insufficient. Therefore, its profit is less than ImpGTA when $| W |$ is small. When $\vert W \vert$ gets larger, the profit of GTA algorithms becomes similar and the profit growth of all the algorithms slows down. 

The reason is that there are enough idle workers and most tasks are served. 

Total Profit w.r.t $| T |$ . We change $| T |$ from $1 0 \mathrm { k }$ to $5 0 0 \mathrm { k }$ and the profit is shown in Fig. 6(d). With the increase of $| T |$ , there are more tasks to be served which improves the total profit. ImpGTA and RamCOM are better than others because they use threshold to select valuable tasks. The results verify that the dynamic threshold of ImpGTA can achieve better results than RamCOM. With the increase of $| T |$ , the gap among ImpGTA and other algorithms becomes larger. 

Total Profit w.r.t radw. We change $r a d _ { w }$ from 0.5 to 2.5 and the total profit is shown in Fig. 6(g). With the increase of $r a d _ { w }$ , all the algorithms achieve better results. Although $\vert W \vert$ and $| T |$ have not changed, the larger radius allows workers to serve more tasks, which leads to the improvement of the total profit. When $r a d _ { w } = 0 . 5$ , there are too few tasks that workers can serve, so the total profit of GTA algorithms are similar. With the increase of the $r a d _ { w }$ , it verify the effectiveness of ImpGTA. Meanwhile, the results of BaseGTA and COM algorithms are similar when $r a d _ { w } = 2 . 5$ . 

Total Profit w.r.t $u _ { w }$ . We change $u _ { w }$ from 2.0 to 6.0 and the total profit is shown in Fig. 6(j). As TOTA and COM algorithms are independent of $u _ { w }$ , their profit keeps unchanged. The profit of BaseGTA keeps unchanged when $u _ { w } < 5$ . The reason is that the payment is less than the minimum reward of tasks and the it does not change the tasks that are served. When $u _ { w } \leq 5$ , the profit of ImpGTA increases due to it can filter tasks with higher reward. Different from ImpGTA, the profit of BaseGTA keeps unchanged until $u _ { w } = 5$ . The reason is that the payment may exceed the minimum reward and these low reward tasks may be rejected. Then, workers are not occupied by these low reward tasks and have the opportunity to serve high reward tasks. When $u _ { w } \geq 6$ , the profit of GTA algorithms decreases because the payment is larger than the reward of most tasks which decreases the number of tasks that are served. 

Total Profit w.r.t $\Delta \tau$ . We change $\Delta \tau$ from 1 to 15 minutes and the total profit is shown in Fig. 6(m). As TOTA, COM algorithms and BaseGTA are independent of $\Delta \tau$ , their profit keeps unchanged. We observe that with the increase of $\Delta \tau$ , the total profit of ImpGTA increases when $\Delta \tau < 3$ and then decreases. When $\Delta \tau$ is equal to 1 minute, the temporal window is too short, and the prediction results can not support the platform to make decisions. When $\Delta \tau$ is too long, the prediction results are more accurate, but there may be a huge gap between the 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/9fae363a043f153cb9473f8bb91e5e33c209b535d15147facf8aa46a9d1a7113.jpg)



(a) Total profit w.r.t. |W|


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/fc8fab7ae200f82de713f0a7f2c927f711620039ac582c595450ae4d0512481d.jpg)



(b) Acceptance ratio w.r.t. $| W |$


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/4af7fb80a8b8bb12f20522ba1f697df05c4739d2833b3c769d4218aae7fd2fb0.jpg)



(c) Payment ratio w.r.t. |W|


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/72c3ea3ad79810cb4b49d5871baa109ae2f58387bcc6de24c61e9136943a52fd.jpg)



(d) Total profit w.r.t. $| \pmb { T } |$


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/3c4c3c323ae99dfdd49c62fd114a0632b98a20f58e20fac4fbf1f536863eacec.jpg)



(e) Acceptance ratio w.r.t. $| \pmb { T } |$


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/bebaa4c7faff511ab84fd3a4beddcb5637f43d2dfa4482a1bf9d650de1a7dbf5.jpg)



(f) Payment ratio w.r.t. $| T |$


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/746e47c1275b3e08d7120cb3cfd468e9bfa63c90966c7568ae6ee27514797689.jpg)



(g) Total profit w.r.t. radw


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/b524c24d8af750fff957276d02bfe289a8f51b69f67d56ec0910742559f9224e.jpg)



(h) Acceptance ratio w.r.t. radw


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/7db6cc2db2e5bc4a8e07394ef86e4b80f43e601d69a44636b1c663154cb2d059.jpg)



(i) Payment ratio w.r.t. radw


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/aa88ae03f563ca1d67a0ee525f07b3a23d266a11c09955425b207e71bea48102.jpg)



(j) Total profit w.r.t. $u _ { w }$


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/cdeee7402e75c0aea1d97f1a93d78061766ef036d55afa7bb3695b97e5ec8e40.jpg)



(k) Acceptance ratio w.r.t. $u _ { w }$


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/576649010248e305af089e4a1fc9f9809de0d4842b94ecf7c3d2cb509eabe6e4.jpg)



(l) Payment ratio w.r.t. $u _ { w }$


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/ace6e02a1008c7490bf5bef6ae638f511edfea65c33811683e468fc2b36e04d2.jpg)



(m) Total profit w.r.t.△T


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/87535d4c32dfa6e8d5805865a6251965445e30357a2e95c83c1cbfa04f13a3b4.jpg)



(n) Acceptance ratio w.r.t.△T


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/8a5e62d7ba664fe00f2430ed45ae6e12c884ed3038c33c0d492a09ca4898b5cb.jpg)



(o) Payment ratio w.r.t.△T



Fig. 6. Scalability on synthetic datasets.


arrival time of the tasks and workers, which reduces the matching profit. 

Acceptance Ratio w.r.t $\vert W \vert$ . We change $| W |$ from $1 \mathrm { k \Omega }$ to $1 0 \mathrm { k }$ and the acceptance ratio is shown in Fig. 6(b). With the increase of $| W |$ , the acceptance ratio of all cooperative algorithms increases. The reason is that the number of idle workers increases, and tasks are more likely to be accepted. Because TOTA does not involve cooperation, its acceptance ratio has always been 0. Although both DemCOM and BaseGTA are in green manner, the acceptance ratio of BaseGTA is higher than that of DemCOM. In Demcom, the payment is two low so that many tasks are rejected by workers. On the country, platforms in GTA algorithms do not reject the tasks if the outer policies are satisfied. The acceptance ratio of RamCOM is higher than others because the payment is an expected value which is more likely to be accepted. To improve the profit, ImpGTA considers the global distribution. The inner policy makes more tasks become outer tasks and the outer policy filters out the tasks with low payment. Therefore, it results in a lower acceptance rate. 

Acceptance Ratio w.r.t $| T |$ . We change $| T |$ from $1 0 \mathrm { k }$ to $5 0 0 \mathrm { k }$ and the acceptance ratio is shown in Fig. 6(e). With the increase of $| T |$ , the acceptance ratio of all algorithms decreases. The reason is that each platform sends a large number of tasks to outer platforms but the number of workers keeps unchanged. Meanwhile, the number of accepted tasks grows slowly, resulting in the decrease of the acceptance ratio. ImpGTA considers the future distribution and rejects unsuitable outer tasks, so the acceptance rate is lower than that of other algorithms. 

Acceptance Ratio w.r.t radw. We change $r a d _ { w }$ from 0.5 to 2.5 and the acceptance ratio is shown in Fig. 6(h). The increase of $r a d _ { w }$ slightly improves the acceptance ratio. The reason for the increase is that workers can serve more tasks, so the number of idle workers for each task increases. It results in the increase of the acceptance ratio. 

Acceptance Ratio w.r.t $u _ { w }$ . We change $u _ { w }$ from 2.0 to 6.0 and the acceptance ratio is shown in Fig. 6(k). The change of $u _ { w }$ does not influence the acceptance ratio of DemCOM and RamCOM. The acceptance ratio of BaseGTA starts to decrease when $u _ { w } \geq 5$ . When $u _ { w } = 5$ , the payment exceeds the reward of some tasks, and these tasks will be rejected. When $u _ { w }$ gets larger, the payment will be larger than more tasks. Therefore, the acceptance ratio will decrease. When $u _ { w } > 6$ , the probability that the outer condition can be satisfied decreases, and the tasks will not be accepted by the outer platforms. Therefore, the acceptance ratio of ImpGTA also begins to decrease. 

Acceptance Ratio w.r.t $\Delta \tau$ . We change $\Delta \tau$ from 1 to 15 minutes and the acceptance ratio is shown in Fig. 6(n). The change of $\Delta \tau$ still only influence ImpGTA. With the increase of $\Delta \tau$ , the acceptance ratio gradually decreases. In this process, the platform can better judge the order change trend in the future. Therefore, they may focus high-reward tasks and reject lowreward tasks from other platforms, thus reducing the acceptance ratio. 

Payment Ratio w.r.t $| W |$ . We change $\vert W \vert$ from $1 \mathrm { ~ k ~ }$ to $1 0 ~ \mathrm { k }$ and the payment ratio is shown in Fig. 6(b). The increase of $| W |$ 

has little influence on the payment ratio of COM algorithms and the payment ratio of GTA algorithms decreases. The increase of $| W |$ brings more idle workers and may reduce the critical payment when GTA algorithms select a winner with the minimum dispatching price. Therefore, the payment ratio decreases. 

Payment Ratio w.r.t $| T |$ . We change $| T |$ from $1 0 ~ \mathrm { k }$ to $5 0 0 \mathrm { k }$ and the payment ratio is shown in Fig. 6(f). With the increase of $| T |$ , workers can serve more tasks which decreases the number of idle workers when a task is submitted. The payment ratio of GTA algorithms increase. The reason is similar when $| W |$ decreases. 

Payment Ratio w.r.t radw. We change $r a d _ { w }$ from 0.5 to 2.5 and the payment ratio is shown in Fig. 6(i). The impact of $r a d _ { w }$ to payment ratio is inapparent. The payment ratio of GTA algorithms increases slightly. Because more tasks are served, and the number of idle workers reduces. Therefore, the travel cost may increase leading to the increase of payment ratio. 

Payment Ratio w.r.t $u _ { w }$ . We change $u _ { w }$ from 2.0 to 6.0 and the payment ratio is shown in Fig. 6(l). $u _ { w }$ does not influence the payment ratio of the COM algorithms. As the payment of the GTA algorithms is related to $u _ { w }$ , so the increase of $u _ { w }$ directly improves the payment ratio. When $u _ { w } > 5$ , the payment ratio increases slowly. The reason is that many bidding prices exceed the order price, so they are rejected. 

Payment Ratio w.r.t $\Delta \tau$ . We change $\Delta \tau$ from 1 to 15 minutes and the payment ratio is shown in Fig. 6(o). With the increase of $\Delta \tau$ , the payment ratio gradually decreases. The number of matched tasks decreases, the number of idle workers increases. Therefore, the critical payment may also decrease, resulting in a decrease of the payment ratio. 

Memory Cost w.r.t |W |, $| T |$ , $r a d _ { w }$ , $u _ { w }$ and $\Delta \tau$ . The memory cost with different parameters are shown in the first row of Figs. 7 and 8(a). When $\vert W \vert$ and $| T |$ increase, all algorithms need more space to store data, so the memory cost increases as shown in Fig. 7(a) and (b). When $r a d _ { w }$ , $u _ { w }$ , $\Delta \tau$ increases, it has a little influence on the memory cost as shown in Figs. 7(a), (d) and 8(a). ImpGTA consumes the most memory in all the cases, but it is still acceptable. 

Response Time w.r.t $\vert W \vert$ , $| T |$ , $r a d _ { w }$ , $u _ { w }$ and $\Delta \tau$ . The response time of a single task is related to the overall number of idle workers. Because it is necessary to enumerate all idle workers while dispatching workers to tasks, so as to select a suitable one. With the increase of $| W |$ , idle workers increases significantly, so the response time has gradually increased as shown in Fig. 7(e). With the increase of $| T |$ , the probability of workers being assigned tasks is greatly improved. The number of idle workers decreases. Therefore, the response time becomes shorter as shown in Fig. 7(g). As $r a d _ { w }$ increases, the number idle workers also decreases because workers have more tasks to serve. So the response time becomes shorter as shown in Fig. 7(g). $u _ { w }$ has little effect on the response time, and the response time of each algorithm fluctuates as shown in Fig. 7(h). The increase of $\Delta \tau$ costs more time for ImpGTA to response a task and other algorithms are not influenced by $\Delta \tau$ as shown in Fig. 8(b). 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/fd2b981ec7725b3499e0443c127a1f06d8e3521ab6d15682bef269d158a6991e.jpg)



(a) Memory cost w.r.t. $\vert W \vert$


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/4507b59ea7db2348ec9ca44edbcd68bbd9202e31bd225de3039460715300d4f7.jpg)



(b) Memory cost w.r.t. $| T |$


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/0cbeb3e25c6fd455db4f6eb5fb29e23c10e25d082ab23ce2c6e50e650b59ac28.jpg)



(c) Memory cost w.r.t. radw


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/3315f85bc661af5b22416ee66b014858fd733d963369f5250f63ba7e27e5ec5b.jpg)



(d) Memory cost w.r.t. $u _ { w }$


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/efd914a81328e40cfbc3962a76d92d9d55a91aa04cb66e0b1e1f69133ce07686.jpg)



(e) Response time w.r.t. $| W |$


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/fd87050db14c70a9fccadc12b7d12587c0bb048eff5817c16e26c50da7699df0.jpg)



(f) Response time w.r.t. $| T |$


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/ced0b0524e737868f789f1fe9367540e2b77c5be0f28e8cc247fa7511e5743ed.jpg)



(g) Response time w.r.t. radw


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/f2c489dff934edb3739712f5833b07914b474c9d470e020c40e798d3a8f3a008.jpg)



(h) Response time w.r.t. $u _ { w }$



Fig. 7. Scalability on Synthetic datasets.


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/bc70cbaf53d64c0535007c321d54ff00bda13251ef777fb708a6cf45e3d67f27.jpg)



(a) Memory cost w.r.t. △T


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/67fdb1e51057c44089c2f888fed510c93ade01d47d8cf2055077145db2ce05b5.jpg)



(b) Response time w.r.t.△T



Fig. 8. Scalability on Synthetic datasets.


# VII. CONCLUSION

In this paper, we propose the Global Task Assignment problem (GTA) in online spatial crowdsourcing platforms. Similar platforms can form an alliance and hire idle workers from each other. In this problem, the platforms start to cooperate rather than compete with others to improve the profit together. GTA is proved to be NP-hard. To solve GTA, we propose an auctionbased incentive mechanism (AIM) and two task dispatching algorithms, BaseGTA and ImpGTA. BaseGTA assigns tasks in a greedy manner and ImpGTA uses a global distribution to guide the task assignment. Through the experiments on real and synthetic datasets, our algorithm can achieve better results than existing studies. 

# REFERENCES



[1] Y. Tong, Z. Zhou, Y. Zeng, L. Chen, and C. Shahabi, “Spatial crowdsourcing: A survey,” VLDB J., vol. 29, no. 1, pp. 217–250, 2020. 





[2] S. R. B. Gummidi, X. Xie, and T. B. Pedersen, “A survey of spatial crowdsourcing,” ACM Trans. Database Syst., vol. 44, no. 2, pp. 8:1–8:46, 2019. 





[3] F. Tang, “Optimal complex task assignment in service crowdsourcing,” in Proc. 29th Int. Joint Conf. Artif. Intell., 2020, pp. 1563–1569. 





[4] Y. Zhao et al., “Preference-aware task assignment in spatial crowdsourcing,” in Proc. 33rd AAAI Conf. Artif. Intell., 2019, pp. 2629–2636. 





[5] Y. Tong, Y. Zeng, B. Ding, L. Wang, and L. Chen, “Two-sided online microtask assignment in spatial crowdsourcing,” IEEE Trans. Knowl. Data Eng., vol. 33, no. 5, pp. 2295–2309, May 2021. 





[6] D. Shi, Y. Tong, Z. Zhou, B. Song, W. Lv, and Q. Yang, “Learning to assign: Towards fair task assignment in large-scale ride hailing,” in Proc. 27th ACM SIGKDD Conf. Knowl. Discov. Data Mining, 2021, pp. 3549–3557. 





[7] Z. Chen, P. Cheng, Y. Zeng, and L. Chen, “Minimizing maximum delay of task assignment in spatial crowdsourcing,” in Proc. IEEE 35th Int. Conf. Data Eng., 2019, pp. 1454–1465. 





[8] Y. Tong, J. She, B. Ding, L. Chen, T. Wo, and K. Xu, “Online minimum matching in real-time spatial data: Experiments and analysis,” Proc. VLDB Endowment, vol. 9, no. 12, pp. 1053–1064, 2016. 





[9] Y. Cheng, B. Li, X. Zhou, Y. Yuan, G. Wang, and L. Chen, “Real-time cross online matching in spatial crowdsourcing,” in Proc. IEEE 36th Int. Conf. Data Eng., 2020, pp. 1–12. 





[10] J. Liu and K. Xu, “Budget-aware online task assignment in spatial crowdsourcing,” World Wide Web, vol. 23, no. 1, pp. 289–311, 2020. 





[11] P. Cheng, X. Jian, and L. Chen, “An experimental evaluation of task assignment in spatial crowdsourcing,” Proc. VLDB Endowment, vol. 11, no. 11, pp. 1428–1440, 2018. 





[12] X. Tang et al., “A deep value-network based approach for multi-driver order dispatching,” in Proc. 25th ACM SIGKDD Int. Conf. Knowl. Discov. Data Mining, 2019, pp. 1780–1790. 





[13] L. Kazemi and C. Shahabi, “Geocrowd: Enabling query answering with spatial crowdsourcing,” in Proc. Int. Conf. Adv. Geographic Inf. Syst., 2012, pp. 189–198. 





[14] J. She, Y. Tong, L. Chen, and T. Song, “Feedback-aware social eventparticipant arrangement,” in Proc. ACM Int. Conf. Manage. Data, 2017, pp. 851–865. 





[15] D. Deng, C. Shahabi, and U. Demiryurek, “Maximizing the number of worker’s self-selected tasks in spatial crowdsourcing,” in Proc. 21st SIGSPATIAL Int. Conf. Adv. Geographic Inf. Syst., 2013, pp. 314–323. 





[16] P. Cheng, X. Lian, L. Chen, J. Han, and J. Zhao, “Task assignment on multi-skill oriented spatial crowdsourcing,” IEEE Trans. Knowl. Data Eng., vol. 28, no. 8, pp. 2201–2215, Aug. 2016. 





[17] B. Li, Y. Cheng, Y. Yuan, G. Wang, and L. Chen, “Three-dimensional stable matching problem for spatial crowdsourcing platforms,” in Proc. 25th ACM SIGKDD Int. Conf. Knowl. Discov. Data Mining, 2019, pp. 1643– 1653. 





[18] X. Yu, G. Li, Y. Zheng, Y. Huang, S. Zhang, and F. Chen, “CrowdOTA: An online task assignment system in crowdsourcing,” in Proc. IEEE 34th Int. Conf. Data Eng., 2018, pp. 1629–1632. 





[19] Y. Tong et al., “Flexible online task assignment in real-time spatial data,” Proc. VLDB Endowment, vol. 10, no. 11, pp. 1334–1345, 2017. 





[20] Y. Tong, J. She, B. Ding, L. Wang, and L. Chen, “Online mobile micro-task allocation in spatial crowdsourcing,” in Proc. IEEE 32nd Int. Conf. Data Eng., 2016, pp. 49–60. 





[21] P. Xu et al., “A unified approach to online matching with conflict-aware constraints,” in Proc. 33rd AAAI Conf. Artif. Intell., 2019, pp. 2221–2228. 





[22] P. Cheng, X. Lian, L. Chen, and C. Shahabi, “Prediction-based task assignment in spatial crowdsourcing,” in Proc. IEEE 33rd Int. Conf. Data Eng., 2017, pp. 997–1008. 





[23] Z. Wang, Y. Zhao, X. Chen, and K. Zheng, “Task assignment with worker churn prediction in spatial crowdsourcing,” in Proc. 30th ACM Int. Conf. Inf. Knowl. Manage., 2021, pp. 2070–2079. 





[24] Z. Liu, K. Li, X. Zhou, N. Zhu, Y. Gao, and K. Li, “Multi-stage complex task assignment in spatial crowdsourcing,” Inf. Sci., vol. 586, pp. 119–139, 2022. 





[25] Y. Zhao, K. Zheng, J. Guo, B. Yang, T. B. Pedersen, and C. S. Jensen, “Fairness-aware task assignment in spatial crowdsourcing: Gametheoretic approaches,” in Proc. IEEE 37th Int. Conf. Data Eng., 2021, pp. 265–276. 





[26] C. F. Costa and M. A. Nascimento, “Online in-route task selection in spatial crowdsourcing,” in Proc. 28th Int. Conf. Adv. Geographic Inf. Syst., 2020, pp. 239–250. 





[27] T. Song et al., “Trichromatic online matching in real-time spatial crowdsourcing,” in Proc. IEEE 33rd Int. Conf. Data Eng., 2017, pp. 1009–1020. 





[28] W. Peng, A. Liu, Z. Li, G. Liu, and Q. Li, “User experience-driven secure task assignment in spatial crowdsourcing,” World Wide Web, vol. 23, no. 3, pp. 2131–2151, 2020. 





[29] J. Zhang, F. Yang, Z. Ma, Z. Wang, X. Liu, and J. Ma, “A decentralized location privacy-preserving spatial crowdsourcing for internet of vehicles,” IEEE Trans. Intell. Transp. Syst., vol. 22, no. 4, pp. 2299–2313, Apr. 2021. 





[30] F. T. Islam, T. Hashem, and R. Shahriyar, “A privacy-enhanced and personalized safe route planner with crowdsourced data and computation,” in Proc. IEEE 37th Int. Conf. Data Eng., 2021, pp. 229–240. 





[31] H. To, G. Ghinita, and C. Shahabi, “A framework for protecting worker location privacy in spatial crowdsourcing,” Proc. VLDB Endowment, vol. 7, no. 10, pp. 919–930, 2014. 





[32] H. To, C. Shahabi, and L. Xiong, “Privacy-preserving online task assignment in spatial crowdsourcing with untrusted server,” in Proc. IEEE 34th Int. Conf. Data Eng., 2018, pp. 833–844. 





[33] Q. Tao, Y. Tong, Z. Zhou, Y. Shi, L. Chen, and K. Xu, “Differentially private online task assignment in spatial crowdsourcing: A tree-based approach,” in Proc. IEEE 36th Int. Conf. Data Eng., 2020, pp. 517–528. 





[34] N. B. Shah and D. Zhou, “Double or nothing: Multiplicative incentive mechanisms for crowdsourcing,” in Proc. Adv. Neural Inf. Process. Syst. 28: Annu. Conf. Neural Inf. Process. Syst., 2015, pp. 1–9. 





[35] Z. Wang, Y. Huang, X. Wang, J. Ren, Q. Wang, and L. Wu, “SocialRecruiter: Dynamic incentive mechanism for mobile crowdsourcing worker recruitment with social networks,” IEEE Trans. Mobile Comput., vol. 20, no. 5, pp. 2055–2066, May 2021. 





[36] G. Gao, M. Xiao, J. Wu, L. Huang, and C. Hu, “Truthful incentive mechanism for nondeterministic crowdsensing with vehicles,” IEEE Trans. Mobile Comput., vol. 17, no. 12, pp. 2982–2997, Dec. 2018. 





[37] X. Wang, W. Tushar, C. Yuen, and X. Zhang, “Promoting users’ participation in mobile crowdsourcing: A distributed truthful incentive mechanism (DTIM) approach,” IEEE Trans. Veh. Technol., vol. 69, no. 5, pp. 5570– 5582, May 2020. 





[38] Y. Tong, L. Wang, Z. Zhou, L. Chen, B. Du, and J. Ye, “Dynamic pricing in spatial crowdsourcing: A matching-based approach,” in Proc. Int. Conf. Manage. Data, 2018, pp. 773–788. 





[39] F. Tian, B. Liu, X. Sun, X. Zhang, G. Cao, and L. Gui, “Movement-based incentive for crowdsourcing,” IEEE Trans. Veh. Technol., vol. 66, no. 8, pp. 7223–7233, Aug. 2017. 





[40] H. Guda and U. Subramanian, “Your uber is arriving: Managing ondemand workers through surge pricing, forecast communication, and worker incentives,” Manage. Sci., vol. 65, no. 5, pp. 1995–2014, 2019. 





[41] D. Yang, G. Xue, X. Fang, and J. Tang, “Crowdsourcing to smartphones: Incentive mechanism design for mobile phone sensing,” in Proc. 18th Annu. Int. Conf. Mobile Comput. Netw., 2012, pp. 173–184. 





[42] J. Zhang, D. Wen, and S. Zeng, “A discounted trade reduction mechanism for dynamic ridesharing pricing,” IEEE Trans. Intell. Transp. Syst., vol. 17, no. 6, pp. 1586–1595, Jun. 2016. 





[43] M. Xiao et al., “SRA: Secure reverse auction for task assignment in spatial crowdsourcing,” IEEE Trans. Knowl. Data Eng., vol. 32, no. 4, pp. 782– 796, Apr. 2020. 





[44] Y. Yue, W. Sun, J. Liu, and Y. Jiang, “Ai-enhanced incentive design for crowdsourcing in internet of vehicles,” in Proc. IEEE 90th Veh. Technol. Conf., 2019, pp. 1–5. 





[45] A. Mehta, “Online matching and ad allocation,” Found. Trends Theor. Comput. Sci., vol. 8, no. 4, pp. 265–368, 2013. 





[46] N. Nisan, T. Roughgarden, É. Tardos, and V. V. Vazirani, Eds., Algorithmic Game Theory. New York, NY, USA: Cambridge Univ. Press, 2007. 





[47] Q. Hu, L. Ming, R. Xi, L. Chen, C. S. Jensen, and B. Zheng, “SOUP: A fleet management system for passenger demand prediction and competitive taxi supply,” in Proc. IEEE 37th Int. Conf. Data Eng., 2021, pp. 2657–2660. 



![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/a52473a5742606da49df9f6201a4dcdffdca9ad24cf756ac770530b4839db02c.jpg)


Boyang Li received the BS and PhD degrees from the College of Computer Science and Engineering of Northeastern University, China, in 2015 and 2020, respectively. Currently, he is a postdoc in computer science with the Beijing Institute of Technology. His main research interests include social networks, spatio-temporal databases, and machine learning. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/d86cd2c6088ed83bcb2faf7b00a13e7a9d8a8e66f0f7725173422b30aed19d22.jpg)


Yurong Cheng (Member, IEEE) received the BS and PhD degrees from the College of Computer Science and Engineering of Northeastern University, China, in 2012 and 2017, respectively. Currently, she is an associate professor in computer science with the Beijing Institute of Technology. Her main research interests include queries and analysis over uncertain graphs, knowledge bases, social networks, and spatiotemporal databases. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/23e257b07a012376cae18cc0aa19a7ffbc53f7ba8368197e365dc1d26bedf0a6.jpg)


Ye Yuan (Member, IEEE) received the BS, MS, and PhD degrees in computer science from Northeastern University, in 2004, 2007, and 2011, respectively. He is currently a professor with the Department of Computer Science, Beijing Institute of Technology, Beijing, China. His research interests include graph databases, probabilistic databases, and social network analysis. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/913ea514ecf8451fd852301b4be3a1ce97d31ca63b7598eb44a0e987c1423f6a.jpg)


Changsheng Li (Member, IEEE) received the BE degree from the University of Electronic Science and Technology of China (UESTC), in 2008 and the PhD degree in pattern recognition and intelligent system from the Institute of Automation, Chinese Academy of Sciences, in 2013. He is currently a professor with the Beijing Institute of Technology. His research interests include machine learning, data mining, and computer vision. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/64cd70ccf7d8485753b7f559a696c46485d85553f770a786a8a90e67cf90c027.jpg)


Qianqian Jin is currently working toward the master’s degree in the School of Computer Science and Technology, Beijing Institute of Technology, Beijing, China. Her major research interests include crowdsourcing and spate-temporal data analysis. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/a262577d-6d63-4e7c-9002-52b423a9ee7b/97d031c0c8d48733d5e28ba879b90ec6a7eeb2e2912c02e59957c34d3772b294.jpg)


Guoren Wang received the BSc, MSc, and PhD degrees in computer science from Northeastern University, China, in 1988, 1991, and 1996, respectively. Currently, he is a professor with the Department of Computer Science, Beijing Institute of Technology, China. His research interests include XML data management, query processing and optimization, bioinformatics, high-dimensional indexing, parallel database systems, and P2P data management. 