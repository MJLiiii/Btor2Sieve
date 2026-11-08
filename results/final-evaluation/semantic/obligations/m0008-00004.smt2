(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_4 () (_ BitVec 1))
(declare-fun s_3 () (_ BitVec 1))
(assert
 (not (= (ite (= s_3 s_4) (_ bv1 1) (_ bv0 1)) (_ bv1 1))))
(assert
 (let (($x6963 (= s_3 s_4)))
(let ((?x508 (ite $x6963 (_ bv1 1) (_ bv0 1))))
(let (($x6949 (= ?x508 s_4)))
(not $x6949)))))
(check-sat)
