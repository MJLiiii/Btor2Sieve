(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_5 () (_ BitVec 8))
(declare-fun s_5_next () (_ BitVec 8))
(assert
 (let (($x21 (and (= s_5_next (bvadd s_5 (_ bv1 8))))))
(and $x21 true)))
(check-sat)
