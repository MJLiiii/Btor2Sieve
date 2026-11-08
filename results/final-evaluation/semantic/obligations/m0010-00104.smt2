(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x3317 (and (distinct i_6 (_ bv255 8)) true)))
(not $x3317)))
(check-sat)
