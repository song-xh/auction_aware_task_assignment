Editor Comments

Senior Editor: 1
Comments to the Author:
(There are no comments. Please check to see if comments were included as a file attachment with this e-mail or as an attachment in your Author Center.)

Associate Editor: 2
Comments to the Author:
The reviewers have made a few suggestions to improve the paper. Please read the reviews for detailed comments. The authors are suggested to address them and submit a revision.  

**************************
Reviewer: 1

Recommendation: Author Should Prepare A Major Revision For A Second Review

Comments:
This paper makes a clear and meaningful contribution by studying cross-platform urban logistics, where a local platform can temporarily use couriers from other platforms, which is more realistic than the single-platform settings used in most prior work. The proposed dual-layer auction explicitly considers incentives at both the courier level and the platform level, addressing a key gap in earlier cross-platform matching studies that assume cooperation without proper compensation. The paper further integrates this auction mechanism into an end-to-end online assignment framework, showing how local matching, cross-platform assignment, and revenue optimization work together in practice. The reinforcement-learning extension adds adaptivity for batch sizing and cross-or-local decisions, and the experimental evaluation is reasonably thorough, demonstrating improved revenue and task completion under a wide range of settings.

Here are the weak points:
W1. The proposed approach is evaluated in a simulated environment and relies on strong assumptions about rational behavior, accurate data, and stable cross-platform cooperation. In real-world settings, many uncontrolled factors—such as noisy or delayed data, strategic behavior by platforms and couriers, contractual and regulatory constraints, and human decision variability—may break these assumptions. As a result, the method’s effectiveness and deployability in practical, large-scale logistics systems remain uncertain without validation in real operational environments or human-in-the-loop studies.
W2. The method introduces dual-layer auctions, batch processing, and reinforcement learning, all operating in near real time. However, the paper does not fully analyze the communication overhead, latency, and synchronization costs when many platforms and couriers participate simultaneously. In large cities with frequent parcel arrivals, repeated cross-platform auctions and RL decision updates may introduce delays or instability that are not captured in the current simulation-based evaluation.
W3 The method assumes competing platforms will share real-time data and allow cross-platform dispatching, which is not validated and may not hold in real markets.
W4 The paper claims truthfulness, but courier and platform “bids” are largely computed by system-defined formulas rather than reported private valuations. As a result, participants have limited strategic freedom, and the mechanism does not satisfy classical incentive-compatibility assumptions. This weakens the theoretical soundness of the auction model.
W5 The effectiveness of the auction and revenue outcomes relies heavily on several manually chosen parameters (e.g., sharing rates, thresholds, cost ratios). The paper lacks sensitivity analysis or adaptive mechanisms, raising concerns about robustness across different cities, platforms, and workload conditions.

Additional Questions:

1. Which category describes this manuscript?: Research/Technology



2. How relevant is this manuscript to the readers of this periodical? Please explain your rating under Public Comments below.: Relevant



1. Please explain how this manuscript advances this field of research and/or contributes something new to the literature.: This paper advances research on crowdsourced urban logistics by moving from single-platform delivery optimization to incentive-aware, cross-platform cooperation.


Most prior work assumes that platforms or couriers will cooperate for free, or focuses only on improving matching quality within one platform. This manuscript shows how multiple self-interested platforms can cooperate in a realistic and economically sound way, while still optimizing real-time parcel assignment.

2. Is the manuscript technically sound? Please explain your answer under Public Comments below.: Appears to be - but didn't check completely



1. Are the title, abstract, and keywords appropriate? Please explain under Public Comments below.: Yes



2. Does the manuscript contain sufficient and appropriate references? Please explain under Public Comments below.: References are sufficient and appropriate


If you are suggesting additional references they must be entered in the text box provided.  All suggestions must include full bibliographic information plus a DOI.


If you are not suggesting any references, please type NA.: NA

3. Does the introduction state the objectives of the manuscript in terms that encourage the reader to read on? Please explain your answer under Public Comments below.: Yes



4. How would you rate the organization of the manuscript? Is it focused? Is the length appropriate for the topic? Please explain under Public Comments below.: Satisfactory



5. Please rate the readability of the manuscript. Explain your rating under Public Comments below.: Readable - but requires some effort to understand



6. Should the supplemental material be included? (Click on the Supplementary Files icon to view files): Does not apply, no supplementary files included



7. If yes to 6, should it be accepted:


Please rate the manuscript. Please explain your answer.: Good


Reviewer: 2

Recommendation: Author Should Prepare A Major Revision For A Second Review

Comments:

1. The most important issue for this work is that it fails to discuss the difference between [17] and it. This work is very similar to [17] in problem setting and the framework design. The authors should have a very clear and separate section to do the discuss clearly.
2. Due to the similarity, the authors are required to add the methods in [17] as the baselines in the experimental study to show the real advantages of the proposed methods in this work. The methods in [17] can also solve the problem studied in this paper, thus can be added as baselines.
3. How the RL methods are used to train the model is not shown in the experimental study section. What is the training time? What data is used to training the RL model? The authors are suggested to show the details.


Additional Questions:

1. Which category describes this manuscript?: Research/Technology



2. How relevant is this manuscript to the readers of this periodical? Please explain your rating under Public Comments below.: Relevant



1. Please explain how this manuscript advances this field of research and/or contributes something new to the literature.: This paper proposes a framework to solve the cross-platform task assignment problem for spatial crowdsourcing. To optimize the revenue of the local platform, the authors uses two auction techniques to ensure the cross platform couriers get second lowest pay, which is proved with several theorems. Through experiments, the authors show the effects of the proposed framework. However, I find the authors fail to clearly discuss the difference between this work with "Competition and Cooperation: Global Task Assignment in Spatial Crowdsourcing" ([17] in the reference). [17] is also solve a very similar problem: auction-based task assignment for cross platform spatial crowdsourcing. In addition, most importantly, the authors do not compare with the methods in [17]. In my view, the authors must do the comparison due to the very similarity between this work and [17].



2. Is the manuscript technically sound? Please explain your answer under Public Comments below.: Appears to be - but didn't check completely



1. Are the title, abstract, and keywords appropriate? Please explain under Public Comments below.: Yes



2. Does the manuscript contain sufficient and appropriate references? Please explain under Public Comments below.: References are sufficient and appropriate


If you are suggesting additional references they must be entered in the text box provided.  All suggestions must include full bibliographic information plus a DOI.


If you are not suggesting any references, please type NA.: NA

3. Does the introduction state the objectives of the manuscript in terms that encourage the reader to read on? Please explain your answer under Public Comments below.: Yes



4. How would you rate the organization of the manuscript? Is it focused? Is the length appropriate for the topic? Please explain under Public Comments below.: Satisfactory



5. Please rate the readability of the manuscript. Explain your rating under Public Comments below.: Readable - but requires some effort to understand



6. Should the supplemental material be included? (Click on the Supplementary Files icon to view files): Does not apply, no supplementary files included



7. If yes to 6, should it be accepted:


Please rate the manuscript. Please explain your answer.: Fair


Reviewer: 3

Recommendation: Author Should Prepare A Minor Revision

Comments:
(1) The authors define both drop-off parcel and pick-up parcel at the beginning, but only pick-up parcels are incorporated into the CPUL problem formulation. It would be helpful to clarify the role of drop-off parcels and whether they are considered in the current problem scope.

(2) The task stream is divided into batches, with assignments made at the end of each batch. While this batched approach has clear advantages, it may also introduce certain limitations compared to real-time (instant) matching. A discussion on these potential drawbacks would provide a more balanced view of the design choices.

(3) RL-CAP involves two reinforcement learning-based processes: batch size partitioning (M_b) and cross-or-not parcel assignment (M_m). Although the relationship between these two processes is mentioned, it is not clearly illustrated in Fig. 5. Enhancing the figure to better reflect their interaction would improve readability and understanding.

(4) The literature review covers relevant work on task assignment and auction mechanisms. However, a more critical and comparative discussion of existing methods, highlighting their limitations and how they motivate the proposed approach, would strengthen the positioning of this work.


Additional Questions:

1. Which category describes this manuscript?: Research/Technology



2. How relevant is this manuscript to the readers of this periodical? Please explain your rating under Public Comments below.: Relevant



1. Please explain how this manuscript advances this field of research and/or contributes something new to the literature.: The authors propose an auction-based cooperative task assignment problem in the context of crowdsourced first and last mile logistics, aiming to address two key challenges: incentive mechanism design and adaptive assignment strategies. The problem is well motivated and interesting, and the proposed Cross-Aware Parcel Assignment framework presents a promising solution.



2. Is the manuscript technically sound? Please explain your answer under Public Comments below.: Yes



1. Are the title, abstract, and keywords appropriate? Please explain under Public Comments below.: Yes



2. Does the manuscript contain sufficient and appropriate references? Please explain under Public Comments below.: References are sufficient and appropriate


If you are suggesting additional references they must be entered in the text box provided.  All suggestions must include full bibliographic information plus a DOI.


If you are not suggesting any references, please type NA.: NA

3. Does the introduction state the objectives of the manuscript in terms that encourage the reader to read on? Please explain your answer under Public Comments below.: Yes



4. How would you rate the organization of the manuscript? Is it focused? Is the length appropriate for the topic? Please explain under Public Comments below.: Could be improved



5. Please rate the readability of the manuscript. Explain your rating under Public Comments below.: Easy to read



6. Should the supplemental material be included? (Click on the Supplementary Files icon to view files): Does not apply, no supplementary files included



7. If yes to 6, should it be accepted:


Please rate the manuscript. Please explain your answer.: Good