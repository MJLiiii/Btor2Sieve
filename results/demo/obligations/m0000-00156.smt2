(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_5 () (_ BitVec 8))
(declare-fun s_5_next () (_ BitVec 8))
(assert
 (let ((?x10 (bvadd s_5 (_ bv1 8))))
 (let (($x19 (= s_5_next ?x10)))
 (let (($x21 (and $x19)))
 (and $x21 true)))))
(assert
 (let (($x113 (bvule s_5 (_ bv127 8))))
(not $x113)))
(check-sat)
