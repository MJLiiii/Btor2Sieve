(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_8 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x79 (bvsge i_8 (_ bv15 4))))
(not $x79)))
(check-sat)
