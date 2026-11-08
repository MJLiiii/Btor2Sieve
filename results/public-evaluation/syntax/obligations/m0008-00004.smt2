(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_4 () (_ BitVec 1))
(declare-fun s_3 () (_ BitVec 1))
(assert
 (not (= (ite (= s_3 s_4) (_ bv1 1) (_ bv0 1)) (_ bv1 1))))
(assert
 (let (($x85 (= s_3 s_4)))
(let ((?x2718 (ite $x85 (_ bv1 1) (_ bv0 1))))
(let (($x299 (= ?x2718 s_4)))
(not $x299)))))
(check-sat)
