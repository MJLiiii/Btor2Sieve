(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_4 () (_ BitVec 1))
(declare-fun s_3 () (_ BitVec 1))
(assert
 (not (= (ite (= s_3 s_4) (_ bv1 1) (_ bv0 1)) (_ bv1 1))))
(assert
 (let (($x338 (= s_3 s_4)))
(let ((?x355 (ite $x338 (_ bv1 1) (_ bv0 1))))
(let (($x1046 (and (distinct ?x355 s_4) true)))
(not $x1046)))))
(check-sat)
